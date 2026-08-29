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
import sys
import threading
import tkinter as tk

from siarrn import log, ui_dialogos, ui_tema as tema
from siarrn.base_local import BaseLocal
from siarrn.cliente_api import ClienteApi
from siarrn.config_totem import Config
from siarrn.fila_offline import FilaOffline
from siarrn.leitor_qr import LeitorQR
from siarrn.ui_gestao import TelaGestao
from siarrn.ui_inicio import TelaInicio
from siarrn.ui_totem import TelaTotem

# De quanto em quanto tempo a fila local tenta se esvaziar.
SEGUNDOS_SINCRONIZACAO = 20

# A base de alunos muda pouco; uma vez por hora é mais que suficiente.
SEGUNDOS_BASE = 3600

# Depois disto sem ninguém tocar, o totem volta à tela de início.
#
# O número é um equilíbrio: curto demais e a tela troca na cara de quem está
# procurando o próprio nome devagar; longo demais e o totem passa o intervalo
# inteiro exibindo um campo de busca vazio, em vez do cardápio do dia.
MILISSEGUNDOS_INATIVIDADE = 45_000

QUEBRA = chr(10)


class AplicacaoTotem:
    def __init__(self, argumentos: argparse.Namespace) -> None:
        self._argumentos = argumentos

        log.configurar("totem")
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

        self.tela_inicio = TelaInicio(self.raiz, self.cliente, self.entrar_na_busca)
        self.tela_totem = TelaTotem(
            self.raiz, self.base, self.fila, self.cliente, self.abrir_gestao
        )
        self.tela_gestao: TelaGestao | None = None

        self._inatividade = None

        # A camera le em qualquer tela: na apresentacao, mostrar o cartao
        # registra o almoco sem ninguem tocar em nada.
        self.leitor = LeitorQR(self._codigo_lido)
        self.leitor.iniciar()

        self.tela_inicio.pack(fill="both", expand=True)
        self.tela_inicio.iniciar()

        # Atalho alternativo ao toque triplo no rodapé: em máquina com teclado,
        # é mais rápido para quem trabalha na cozinha.
        self.raiz.bind_all("<Control-Alt-g>", lambda e: self.abrir_gestao())
        self.raiz.bind_all("<Control-Alt-G>", lambda e: self.abrir_gestao())

        # Qualquer toque ou tecla adia a volta à tela de início. O `add="+"`
        # é essencial: sem ele estes bindings substituiriam os das telas, e o
        # campo de busca pararia de receber o que é digitado.
        self.raiz.bind_all("<Key>", self._adiar_inicio, add="+")
        self.raiz.bind_all("<Button>", self._adiar_inicio, add="+")

        self._parar = threading.Event()
        self._iniciar_tarefas_de_fundo()
        self._verificar_camera()

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
    # Alternância de telas
    # -----------------------------------------------------------------------
    def _esconder_tudo(self) -> None:
        self.tela_inicio.parar()
        self.tela_inicio.pack_forget()
        self.tela_totem.pack_forget()
        self._cancelar_inatividade()

    def entrar_na_busca(self) -> None:
        """Alguém tocou na tela de início: hora de procurar o nome."""
        self._esconder_tudo()
        self.tela_totem.pack(fill="both", expand=True)
        self.tela_totem.mostrar_busca()
        self._adiar_inicio()

    def voltar_ao_inicio(self) -> None:
        """Ninguém mexeu por um tempo: volta a mostrar o cardápio e as fotos."""
        self._esconder_tudo()
        self.tela_inicio.pack(fill="both", expand=True)
        self.tela_inicio.iniciar()

    def abrir_gestao(self) -> None:
        if self.tela_gestao is not None:
            return
        pai = self.tela_totem if self.tela_totem.winfo_ismapped() else self.tela_inicio
        if not ui_dialogos.pedir_pin(pai, self.config.pin):
            return
        self._trocar_para_gestao()

    def _trocar_para_gestao(self) -> None:
        self._esconder_tudo()
        self.tela_gestao = TelaGestao(
            self.raiz, self.cliente, self.fila, self.base, self.voltar_ao_totem
        )
        self.tela_gestao.pack(fill="both", expand=True)
        self.tela_gestao.iniciar()

    def voltar_ao_totem(self) -> None:
        if self.tela_gestao is not None:
            self.tela_gestao.parar()
            self.tela_gestao.destroy()
            self.tela_gestao = None
        self.voltar_ao_inicio()

    # -----------------------------------------------------------------------
    # Volta automática à tela de início
    # -----------------------------------------------------------------------
    def _cancelar_inatividade(self) -> None:
        if self._inatividade is not None:
            self.raiz.after_cancel(self._inatividade)
            self._inatividade = None

    def _adiar_inicio(self, _evento=None) -> None:
        self._cancelar_inatividade()
        # Só conta enquanto a busca está na tela. Na gestão alguém pode estar
        # lendo os números sem tocar em nada, e na própria tela de início não
        # há para onde voltar.
        if self.tela_gestao is None and self.tela_totem.winfo_ismapped():
            self._inatividade = self.raiz.after(
                MILISSEGUNDOS_INATIVIDADE, self.voltar_ao_inicio
            )

    # -----------------------------------------------------------------------
    # Cartao lido pela camera
    # -----------------------------------------------------------------------
    def _codigo_lido(self, codigo: str) -> None:
        """Chamado da thread da camera: devolve o trabalho para a interface."""
        self.raiz.after(0, lambda: self._tratar_codigo(codigo))

    def _tratar_codigo(self, codigo: str) -> None:
        """Registra o almoco de quem mostrou o cartao.

        A consulta e local, sobre a copia em disco: o cartao precisa funcionar
        com a rede fora do ar, que e justamente quando o totem mais precisa ser
        rapido.
        """
        if self.tela_gestao is not None:
            return  # alguem esta na cozinha; nao e hora de registrar almoco

        aluno = self.base.por_codigo(codigo)
        if aluno is None:
            # Cartao de outra escola, QR de um cartaz na parede, brincadeira.
            # Nao vale interromper quem estiver usando a tela para avisar.
            self.leitor.esquecer_ultimo()
            return

        if not self.tela_totem.winfo_ismapped():
            self._esconder_tudo()
            self.tela_totem.pack(fill="both", expand=True)

        self.tela_totem.registrar_aluno(aluno, "qr")
        self._adiar_inicio()

    def _verificar_camera(self) -> None:
        """Mantém as telas em dia sobre a câmera estar funcionando.

        A câmera pode abrir depois do totem (leva um instante), ser desconectada
        no meio do almoço, ou ser plugada só na hora. As telas anunciam o cartão
        conforme o estado real, e nunca antes.
        """
        disponivel = self.leitor.disponivel
        self.tela_inicio.definir_cartao_ativo(disponivel)
        self.tela_totem.definir_cartao_ativo(disponivel)
        self.raiz.after(10_000, self._verificar_camera)

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
        try:
            self.raiz.mainloop()
        finally:
            self._parar.set()
            self.leitor.parar()
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

    linhas: list[str] = []

    sem_saida = sys.stdout is None

    def anotar(texto: str = "") -> None:
        """Guarda a linha e também imprime, quando houver para onde imprimir."""
        nonlocal sem_saida
        linhas.append(texto)
        try:
            print(texto)
        except (OSError, ValueError, AttributeError):
            # Compilado sem console e sem redirecionamento, não há saída.
            sem_saida = True

    log.configurar("totem")
    config = Config()
    if argumentos.servidor:
        config.servidor = argumentos.servidor

    cliente = ClienteApi(config)
    base = BaseLocal()
    fila = FilaOffline()

    anotar("SIARRN — verificação do totem")
    anotar(f"  servidor configurado: {config.servidor}")

    no_ar = cliente.no_ar()
    anotar(f"  servidor no ar:       {'sim' if no_ar else 'NÃO'}")

    if no_ar:
        anotar(f"  base atualizada:      {'sim' if base.atualizar(cliente) else 'não'}")

    anotar(f"  alunos em disco:      {base.tamanho()}")
    anotar(f"  fila pendente:        {fila.pendentes()}")

    if base.vazia():
        anotar("\nSem base local e sem servidor: o totem não teria nomes para mostrar.")
        anotar("Rode o servidor ao menos uma vez para o totem baixar a lista.")
        return 1

    # A busca não depende de rede: acontece toda em memória, sobre a cópia local.
    inicio = time.perf_counter()
    encontrados = base.buscar("sil")
    micros = (time.perf_counter() - inicio) * 1_000_000
    anotar(f"  busca local por 'sil': {len(encontrados)} resultados em {micros:.0f} µs")

    if argumentos.registrar:
        amostra = base.amostra(argumentos.registrar)
        anotar(f"\nRegistrando {len(amostra)} almoços...")

        inicio = time.perf_counter()
        for aluno in amostra:
            fila.registrar(aluno, "nome")
        total = (time.perf_counter() - inicio) * 1000

        # O tempo medido aqui é o que a pessoa na fila sente. Se registrar cem
        # almoços demorar, nada mais no sistema importa.
        anotar(f"  gravados em disco:    {total:.0f} ms "
              f"({total / max(1, len(amostra)):.1f} ms por aluno)")
        anotar(f"  pendentes agora:      {fila.pendentes()}")

    if fila.pendentes() and no_ar:
        inicio = time.perf_counter()
        enviados = fila.sincronizar(cliente, base)
        anotar(f"\n  sincronizados:        {enviados} em "
              f"{(time.perf_counter() - inicio) * 1000:.0f} ms")
        anotar(f"  restaram na fila:     {fila.pendentes()}")

    cliente.fechar()
    if sem_saida:
        _mostrar_verificacao(linhas)
    return 0


def _mostrar_verificacao(linhas: list[str]) -> None:
    """Mostra o resultado numa janela quando não há console para lê-lo.

    O totem é compilado sem console — é o certo para um programa que fica em
    tela cheia na fila. Só que a verificação existe justamente para alguém da
    escola conferir a instalação com um duplo clique, e nesse caso o texto não
    teria para onde ir.

    O gatilho é `sys.stdout` ser inutilizável, e não a ausência de terminal:
    rodado com a saída redirecionada — de um script, de outro programa — o
    texto chega ao seu destino, e abrir uma janela ali travaria quem chamou
    esperando alguém clicar em Fechar.
    """
    import tkinter as tk

    janela = tk.Tk()
    janela.title("SIARRN — verificação")
    tema.aplicar_tema(janela)

    tk.Label(
        janela, text="Verificação do totem", bg=tema.COR_PRIMARIA,
        fg=tema.COR_TEXTO_CLARO, font=tema.fonte(17, forte=True),
        anchor="w", padx=tema.px(20), pady=tema.px(14),
    ).pack(fill="x")

    tk.Label(
        janela, text=QUEBRA.join(linhas), bg=tema.COR_CARD, fg=tema.COR_TEXTO,
        font=("Consolas", 10), justify="left", anchor="w",
        padx=tema.px(20), pady=tema.px(16),
    ).pack(fill="both", expand=True)

    tk.Button(
        janela, text="Fechar", command=janela.destroy,
        bg=tema.COR_SECUNDARIA, fg=tema.COR_TEXTO_CLARO,
        font=tema.fonte(12, forte=True), relief="flat", borderwidth=0,
        cursor="hand2", padx=tema.px(20), pady=tema.px(9),
    ).pack(pady=(0, tema.px(16)))

    janela.mainloop()


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
