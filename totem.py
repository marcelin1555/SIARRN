#!/usr/bin/env python3
"""
SIARRN — Totem da fila e painel da cozinha

Um programa, dois modos. O totem fica em tela cheia na fila do almoço; o modo
gestão, atrás de um PIN, é o painel da cozinha. A escola instala o mesmo
programa onde precisar — em duas máquinas, se tiver duas; alternando na mesma,
se só houver uma. Como o equipamento ainda não está definido, essa flexibilidade
não é luxo: é o que permite o sistema existir antes de a direção liberar algo.

    python totem.py --servidor=http://192.168.0.10:8770
    python totem.py --janela          não usa tela cheia (desenvolvimento)
    python totem.py --gestao          abre direto no painel da cozinha
"""
from __future__ import annotations

import argparse
import threading
import tkinter as tk

from siarrn import ui_dialogos, ui_tema as tema
from siarrn.base_local import BaseLocal
from siarrn.cliente_api import ClienteApi
from siarrn.config_totem import Config
from siarrn.fila_offline import FilaOffline
from siarrn.ui_gestao import TelaGestao
from siarrn.ui_totem import TelaTotem

# De quanto em quanto tempo a fila local tenta se esvaziar.
SEGUNDOS_SINCRONIZACAO = 20

# A base de alunos muda pouco; uma vez por hora é mais que suficiente.
SEGUNDOS_BASE = 3600


class AplicacaoTotem:
    def __init__(self, argumentos: argparse.Namespace) -> None:
        self._argumentos = argumentos

        self.config = Config()
        if argumentos.servidor:
            self.config.servidor = argumentos.servidor
            self.config.salvar()

        self.cliente = ClienteApi(self.config)
        self.base = BaseLocal()
        self.fila = FilaOffline()

        self.raiz = tk.Tk()
        self.raiz.title("SIARRN")
        tema.aplicar_tema(self.raiz)

        self._configurar_janela()

        self.tela_totem = TelaTotem(
            self.raiz, self.base, self.fila, self.cliente, self.abrir_gestao
        )
        self.tela_gestao: TelaGestao | None = None
        self.tela_totem.pack(fill="both", expand=True)

        # Atalho alternativo ao toque triplo no rodapé: em máquina com teclado,
        # é mais rápido para quem trabalha na cozinha.
        self.raiz.bind_all("<Control-Alt-g>", lambda e: self.abrir_gestao())
        self.raiz.bind_all("<Control-Alt-G>", lambda e: self.abrir_gestao())

        self._parar = threading.Event()
        self._iniciar_tarefas_de_fundo()

        if argumentos.gestao:
            self._trocar_para_gestao()

    # -----------------------------------------------------------------------
    # Janela
    # -----------------------------------------------------------------------
    def _configurar_janela(self) -> None:
        if self._argumentos.janela:
            self.raiz.geometry("1100x740")
            return

        self.raiz.attributes("-fullscreen", True)
        # Sem saída visível e sem Escape: o totem fica sozinho numa fila com cem
        # adolescentes, e minimizar a janela não pode ser uma das opções deles.
        self.raiz.bind("<Escape>", lambda e: "break")
        self.raiz.protocol("WM_DELETE_WINDOW", lambda: None)

    # -----------------------------------------------------------------------
    # Alternância de modo
    # -----------------------------------------------------------------------
    def abrir_gestao(self) -> None:
        if self.tela_gestao is not None:
            return
        if not ui_dialogos.pedir_pin(self.tela_totem, self.config.pin):
            return
        self._trocar_para_gestao()

    def _trocar_para_gestao(self) -> None:
        self.tela_totem.pack_forget()
        self.tela_gestao = TelaGestao(self.raiz, self.cliente, self.fila, self.voltar_ao_totem)
        self.tela_gestao.pack(fill="both", expand=True)
        self.tela_gestao.iniciar()

    def voltar_ao_totem(self) -> None:
        if self.tela_gestao is not None:
            self.tela_gestao.parar()
            self.tela_gestao.destroy()
            self.tela_gestao = None
        self.tela_totem.pack(fill="both", expand=True)
        self.tela_totem.mostrar_busca()

    # -----------------------------------------------------------------------
    # Tarefas de fundo
    # -----------------------------------------------------------------------
    def _iniciar_tarefas_de_fundo(self) -> None:
        threading.Thread(target=self._laco_de_sincronizacao, daemon=True).start()
        threading.Thread(target=self._laco_da_base, daemon=True).start()

    def _laco_de_sincronizacao(self) -> None:
        """Esvazia a fila local. Roda sempre, mesmo sem rede.

        Quando o servidor voltar, a próxima passagem entrega o que ficou
        acumulado sozinha — ninguém precisa apertar nada.
        """
        # Um respiro antes da primeira tentativa: na inicialização a janela ainda
        # está sendo montada, e disputar a rede com o download da base atrasa as
        # duas coisas.
        self._parar.wait(3)
        while not self._parar.is_set():
            try:
                enviados = self.fila.sincronizar(self.cliente, self.base)
                if enviados:
                    self.raiz.after(0, self.tela_totem.atualizar_status)
            except Exception as erro:  # noqa: BLE001
                # Uma falha aqui não pode matar a thread: se ela morre, a fila
                # para de esvaziar em silêncio e ninguém percebe até o fim do dia.
                print(f"Erro na sincronização: {erro}")
            self._parar.wait(SEGUNDOS_SINCRONIZACAO)

    def _laco_da_base(self) -> None:
        while not self._parar.is_set():
            try:
                if self.base.atualizar(self.cliente):
                    self.raiz.after(0, self.tela_totem.atualizar_status)
            except Exception as erro:  # noqa: BLE001
                print(f"Erro ao atualizar a base: {erro}")
            self._parar.wait(SEGUNDOS_BASE)

    # -----------------------------------------------------------------------
    # Execução
    # -----------------------------------------------------------------------
    def executar(self) -> None:
        # O foco só cola depois que a janela existe de verdade na tela; pedir
        # antes do mainloop não tem efeito, e o totem precisa aceitar digitação
        # sem ninguém clicar no campo primeiro.
        self.raiz.after(120, self.tela_totem.mostrar_busca)
        try:
            self.raiz.mainloop()
        finally:
            self._parar.set()
            # Última tentativa de entregar o que ainda estiver na fila.
            try:
                self.fila.sincronizar(self.cliente, self.base)
            except Exception:  # noqa: BLE001
                pass
            self.cliente.fechar()


def verificar(argumentos: argparse.Namespace) -> int:
    """Confere a instalação sem abrir a interface.

    Serve para dois momentos. No desenvolvimento, é o teste ponta a ponta do
    requisito que mais importa: o totem continua registrando almoços com o
    servidor fora do ar, e depois entrega tudo sem duplicar nada. Na escola, é
    o que se roda para saber se aquela máquina enxerga o servidor antes de a
    fila se formar.
    """
    import time

    config = Config()
    if argumentos.servidor:
        config.servidor = argumentos.servidor

    cliente = ClienteApi(config)
    base = BaseLocal()
    fila = FilaOffline()

    print("SIARRN — verificação do totem")
    print(f"  servidor configurado: {config.servidor}")

    no_ar = cliente.no_ar()
    print(f"  servidor no ar:       {'sim' if no_ar else 'NÃO'}")

    if no_ar:
        print(f"  base atualizada:      {'sim' if base.atualizar(cliente) else 'não'}")

    print(f"  alunos em disco:      {base.tamanho()}")
    print(f"  fila pendente:        {fila.pendentes()}")

    if base.vazia():
        print("\nSem base local e sem servidor: o totem não teria nomes para mostrar.")
        print("Rode o servidor ao menos uma vez para o totem baixar a lista.")
        return 1

    # A busca não depende de rede: acontece toda em memória, sobre a cópia local.
    inicio = time.perf_counter()
    encontrados = base.buscar("sil")
    micros = (time.perf_counter() - inicio) * 1_000_000
    print(f"  busca local por 'sil': {len(encontrados)} resultados em {micros:.0f} µs")

    if argumentos.registrar:
        amostra = base.amostra(argumentos.registrar)
        print(f"\nRegistrando {len(amostra)} almoços...")

        inicio = time.perf_counter()
        for aluno in amostra:
            fila.registrar(aluno, "nome")
        total = (time.perf_counter() - inicio) * 1000

        # O tempo medido aqui é o que a pessoa na fila sente. Se registrar cem
        # almoços demorar, nada mais no sistema importa.
        print(f"  gravados em disco:    {total:.0f} ms "
              f"({total / max(1, len(amostra)):.1f} ms por aluno)")
        print(f"  pendentes agora:      {fila.pendentes()}")

    if fila.pendentes() and no_ar:
        inicio = time.perf_counter()
        enviados = fila.sincronizar(cliente, base)
        print(f"\n  sincronizados:        {enviados} em "
              f"{(time.perf_counter() - inicio) * 1000:.0f} ms")
        print(f"  restaram na fila:     {fila.pendentes()}")

    cliente.fechar()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="totem",
        description="Totem do refeitório e painel da cozinha do SIARRN.",
    )
    parser.add_argument("--servidor", help="endereço do servidor, ex.: http://192.168.0.10:8770")
    parser.add_argument("--janela", action="store_true", help="não abrir em tela cheia")
    parser.add_argument("--gestao", action="store_true", help="abrir direto no painel da cozinha")
    parser.add_argument("--verificar", action="store_true",
                        help="conferir a instalação sem abrir a interface")
    parser.add_argument("--registrar", type=int, metavar="N",
                        help="com --verificar, simula N almoços para medir a fila")
    argumentos = parser.parse_args(argv)

    if argumentos.verificar:
        return verificar(argumentos)

    AplicacaoTotem(argumentos).executar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
