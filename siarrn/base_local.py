"""
SIARRN — Cópia local da lista de alunos

Este módulo é o motivo de o totem não travar quando a rede cai. Toda busca
acontece aqui, em memória, sobre uma lista guardada em disco — nenhuma tecla
digitada na fila depende do servidor. O servidor só é procurado para atualizar
a lista, e mesmo esse contato é opcional: sem ele, o totem trabalha com a cópia
da última vez que conseguiu falar.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import config_totem, log, texto
from .cliente_api import ErroDeRede

# Duas letras é o mínimo. Uma só traria meia escola para a tela.
MINIMO_PARA_BUSCAR = 2

# Lista longa numa fila é pior que lista curta: a pessoa lê tudo em vez de
# achar o próprio nome.
LIMITE_RESULTADOS = 20


class BaseLocal:
    def __init__(self, pasta: Path | None = None) -> None:
        self._arquivo = (pasta or config_totem.PASTA) / "alunos.json"
        self._alunos: list[dict] = []
        self._trava = threading.Lock()
        self._carregar()

    # -----------------------------------------------------------------------
    # Persistência
    # -----------------------------------------------------------------------
    def _carregar(self) -> None:
        if not self._arquivo.is_file():
            return
        try:
            lidos = json.loads(self._arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            log.aviso(f"Base local ilegível, seguindo vazia: {erro}")
            return
        if isinstance(lidos, list):
            with self._trava:
                self._alunos = [self._preparar(a) for a in lidos]

    @staticmethod
    def _preparar(aluno: dict) -> dict:
        """Garante que o nome normalizado esteja pronto antes da fila começar.

        O servidor já manda `nome_busca`, mas um aluno cadastrado no próprio
        totem vem sem ele. Normalizar na hora da busca custaria cento e vinte
        normalizações a cada tecla digitada.
        """
        aluno = dict(aluno)
        if not aluno.get("nome_busca"):
            aluno["nome_busca"] = texto.normalizar(aluno.get("nome", ""))
        return aluno

    def _salvar(self) -> None:
        try:
            self._arquivo.parent.mkdir(parents=True, exist_ok=True)
            with self._trava:
                conteudo = json.dumps(self._alunos, ensure_ascii=False)
            # Escreve num temporário e renomeia: se faltar energia no meio da
            # gravação, o arquivo bom continua lá em vez de virar um pela metade.
            temporario = self._arquivo.with_suffix(".json.tmp")
            temporario.write_text(conteudo, encoding="utf-8")
            os.replace(temporario, self._arquivo)
        except OSError as erro:
            log.aviso(f"Não foi possível salvar a base local: {erro}")

    def atualizar(self, cliente) -> bool:
        """Rebaixa a lista do servidor.

        Devolve False se o servidor não respondeu — caso em que a cópia
        anterior continua valendo e o totem segue funcionando normalmente.
        """
        try:
            novos = cliente.baixar_base()
        except ErroDeRede:
            return False

        if not novos:
            return False

        with self._trava:
            self._alunos = [self._preparar(a) for a in novos]
        self._salvar()
        return True

    def acrescentar(self, aluno: dict) -> None:
        """Inclui um aluno recém-cadastrado sem rebaixar a base inteira."""
        with self._trava:
            self._alunos.append(self._preparar(aluno))
        self._salvar()

    # -----------------------------------------------------------------------
    # Busca
    # -----------------------------------------------------------------------
    def buscar(self, termo: str) -> list[dict]:
        """Alunos cujo nome começa pelo termo, ou que tenham palavra começando por ele."""
        alvo = texto.normalizar(termo)
        if len(alvo) < MINIMO_PARA_BUSCAR:
            return []

        with self._trava:
            encontrados = [
                aluno for aluno in self._alunos
                if texto.combina(aluno["nome_busca"], alvo)
            ]

        encontrados.sort(key=lambda a: a["nome_busca"])
        return encontrados[:LIMITE_RESULTADOS]

    def por_id(self, aluno_id: int) -> dict | None:
        with self._trava:
            for aluno in self._alunos:
                if aluno.get("id") == aluno_id:
                    return aluno
        return None

    def por_codigo(self, codigo: str) -> dict | None:
        """Encontra o aluno pelo código do cartão.

        A busca é local para que o QR funcione com a rede fora do ar — se
        precisasse consultar o servidor, a leitura por câmera deixaria de valer
        exatamente na hora em que o totem mais precisa ser rápido.
        """
        alvo = (codigo or "").strip().upper()
        if not alvo:
            return None

        with self._trava:
            for aluno in self._alunos:
                if (aluno.get("codigo") or "").upper() == alvo:
                    return aluno
        return None

    def amostra(self, quantos: int) -> list[dict]:
        """Alguns alunos quaisquer — usado pela verificação para simular a fila."""
        with self._trava:
            return list(self._alunos[:quantos])

    def tamanho(self) -> int:
        with self._trava:
            return len(self._alunos)

    def vazia(self) -> bool:
        return self.tamanho() == 0
