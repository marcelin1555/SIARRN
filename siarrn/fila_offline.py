"""
SIARRN — Fila de almoços ainda não enviados

É o requisito de sobrevivência do projeto. O totem **nunca** espera o servidor
para responder ao aluno: grava a passagem aqui, mostra a tela verde na hora, e
sincroniza quando der. Se a rede cair com cem pessoas na fila, a fila continua
andando — e é isso que determina se a cozinha vai confiar no sistema no dia
seguinte.

O formato é uma linha de JSON por almoço. Acrescentar uma linha ao fim de um
arquivo é a escrita mais difícil de corromper que existe: se faltar energia no
meio, perde-se no máximo o último registro e o resto continua legível.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from . import config_totem
from .cliente_api import ErroDeRede


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class FilaOffline:
    def __init__(self, pasta: Path | None = None) -> None:
        self._arquivo = (pasta or config_totem.PASTA) / "fila.jsonl"
        self._trava = threading.RLock()

    # -----------------------------------------------------------------------
    # Escrita
    # -----------------------------------------------------------------------
    def _acrescentar(self, item: dict) -> None:
        with self._trava:
            try:
                self._arquivo.parent.mkdir(parents=True, exist_ok=True)
                with open(self._arquivo, "a", encoding="utf-8") as arquivo:
                    arquivo.write(json.dumps(item, ensure_ascii=False) + "\n")
            except OSError as erro:
                # Não há para onde escalar: a pessoa já está com o prato na mão.
                # Registrar no console é tudo o que dá pra fazer sem parar a fila.
                print(f"FALHA AO GRAVAR NA FILA LOCAL: {erro}")

    def registrar(self, aluno: dict, origem: str = "nome") -> None:
        """Registra o almoço de um aluno que já existe na base."""
        self._acrescentar({
            "aluno_id": aluno["id"],
            "registrado_em": agora(),
            "origem": origem,
        })

    def registrar_cadastro_pendente(self, nome: str, turma: str = "") -> None:
        """Registra o almoço de alguém que se cadastrou com o servidor fora do ar.

        Sem isso, quem chegasse novo durante uma queda de rede ficaria sem
        almoçar — e o sistema teria acabado de negar comida a um aluno. O
        cadastro de verdade acontece na sincronização.
        """
        self._acrescentar({
            "aluno_id": None,
            "nome": nome,
            "turma": turma,
            "registrado_em": agora(),
            "origem": "nome",
        })

    # -----------------------------------------------------------------------
    # Leitura
    # -----------------------------------------------------------------------
    def _ler(self) -> list[dict]:
        if not self._arquivo.is_file():
            return []

        itens = []
        try:
            with open(self._arquivo, encoding="utf-8") as arquivo:
                for linha in arquivo:
                    linha = linha.strip()
                    if not linha:
                        continue
                    try:
                        itens.append(json.loads(linha))
                    except ValueError:
                        # Linha truncada por queda de energia. Descartar uma é
                        # melhor que travar a sincronização de todas as outras.
                        print("Linha ilegível na fila, descartada.")
        except OSError as erro:
            print(f"Não foi possível ler a fila local: {erro}")
        return itens

    def pendentes(self) -> int:
        with self._trava:
            return len(self._ler())

    def _reescrever(self, restantes: list[dict]) -> None:
        try:
            if not restantes:
                self._arquivo.unlink(missing_ok=True)
                return
            temporario = self._arquivo.with_suffix(".jsonl.tmp")
            conteudo = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in restantes)
            temporario.write_text(conteudo, encoding="utf-8")
            os.replace(temporario, self._arquivo)
        except OSError as erro:
            print(f"Não foi possível reescrever a fila: {erro}")

    # -----------------------------------------------------------------------
    # Sincronização
    # -----------------------------------------------------------------------
    def sincronizar(self, cliente, base) -> int:
        """Tenta enviar tudo o que está pendente. Devolve quantos foram aceitos.

        Só remove da fila o que o servidor confirmou. Reenviar um almoço já
        registrado é inofensivo — a rota de consumo é idempotente do outro
        lado —, então na dúvida o item permanece e tenta de novo. O erro que
        não se pode cometer é o contrário: apagar da fila algo que nunca chegou.
        """
        with self._trava:
            itens = self._ler()
            if not itens:
                return 0

            restantes: list[dict] = []
            enviados = 0

            for item in itens:
                try:
                    aluno_id = item.get("aluno_id")

                    if aluno_id is None:
                        # Cadastro feito com o servidor fora: cria o aluno agora.
                        criado = cliente.cadastrar(item.get("nome", ""), item.get("turma") or "")
                        base.acrescentar(criado)
                        aluno_id = criado["id"]

                    cliente.registrar_consumo(
                        aluno_id,
                        item.get("registrado_em") or agora(),
                        item.get("origem") or "nome",
                    )
                    enviados += 1
                except (ErroDeRede, KeyError):
                    restantes.append(item)

            self._reescrever(restantes)
            return enviados
