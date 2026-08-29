"""
SIARRN — Impressão dos cartões, no modo gestão

Gera a folha de cartões e a abre no visualizador de PDF do sistema, de onde a
escola imprime em papel comum. Não há integração com impressora: o diálogo de
impressão que a pessoa já conhece resolve melhor do que qualquer tela que eu
fizesse aqui — margens, bandeja, frente e verso, tudo já está lá.

Trabalha sobre a cópia local de alunos, não sobre o servidor. Além de ser
instantâneo, significa que dá para reimprimir o cartão de alguém mesmo com a
rede fora do ar.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config_totem, ui_tema as tema

PASTA_SAIDA = config_totem.PASTA / "cartoes"

# Depois da primeira leva, o que interessa são os alunos que se cadastraram
# desde então. Uma semana cobre o intervalo entre duas impressões sem exigir
# que alguém anote quem já recebeu.
DIAS_RECENTES = 7


def _abrir_no_sistema(caminho: Path) -> None:
    """Abre o PDF no visualizador padrão, em cada sistema operacional."""
    if sys.platform == "win32":
        os.startfile(caminho)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


def _cadastrado_apos(aluno: dict, limite: date) -> bool:
    texto = (aluno.get("criado_em") or "").strip()
    if not texto:
        # Sem data conhecida, entra: é melhor imprimir um cartão a mais do que
        # deixar um aluno sem.
        return True
    try:
        return datetime.strptime(texto[:10], "%Y-%m-%d").date() >= limite
    except ValueError:
        return True


class DialogoCartoes(tk.Toplevel):
    """Escolha de quais cartões gerar."""

    def __init__(self, pai: tk.Misc, base) -> None:
        super().__init__(pai)
        self._base = base
        self._gerando = False

        self.title("SIARRN")
        self.configure(bg=tema.COR_CARD)
        self.transient(pai.winfo_toplevel())
        self.resizable(False, False)

        todos = base.amostra(10_000)
        limite = date.today() - timedelta(days=DIAS_RECENTES)
        self._recentes = [a for a in todos if _cadastrado_apos(a, limite)]
        self._todos = todos

        self._montar()
        self._centralizar()
        self.grab_set()

    def _montar(self) -> None:
        cabecalho = tk.Frame(self, bg=tema.COR_PRIMARIA)
        cabecalho.pack(fill="x")
        tk.Label(
            cabecalho, text="Cartões dos alunos", bg=tema.COR_PRIMARIA,
            fg=tema.COR_TEXTO_CLARO, font=tema.fonte(19, forte=True),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(16), 0))
        tk.Label(
            cabecalho, text="Imprima em papel comum e recorte.",
            bg=tema.COR_PRIMARIA, fg=tema.COR_PRIMARIA_SUAVE, font=tema.fonte(12),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(2), tema.px(16)))

        corpo = tk.Frame(self, bg=tema.COR_CARD)
        corpo.pack(fill="both", expand=True, padx=tema.px(24), pady=tema.px(20))

        self._escolha = tk.StringVar(value="recentes" if self._recentes else "todos")

        self._opcao(
            corpo, "recentes",
            f"Só os {len(self._recentes)} cadastrados nos últimos {DIAS_RECENTES} dias",
            "Para quem entrou depois da última impressão.",
            habilitado=bool(self._recentes),
        )
        self._opcao(
            corpo, "todos",
            f"Todos os {len(self._todos)} alunos",
            f"{self._paginas(len(self._todos))} páginas. Use na primeira vez.",
        )

        self._aviso = tk.Label(
            corpo, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(11), wraplength=tema.px(380), justify="left",
        )
        self._aviso.pack(anchor="w", pady=(tema.px(14), 0))

        rodape = tk.Frame(self, bg=tema.COR_CARD)
        rodape.pack(fill="x", padx=tema.px(24), pady=(0, tema.px(20)))

        tk.Button(
            rodape, text="Fechar", command=self.destroy,
            bg=tema.COR_TEXTO_SUAVE, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(13, forte=True), relief="flat", borderwidth=0,
            cursor="hand2", padx=tema.px(18), pady=tema.px(10),
        ).pack(side="right")

        self._botao_gerar = tk.Button(
            rodape, text="Gerar e abrir", command=self._gerar,
            bg=tema.COR_SUCESSO, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(13, forte=True), relief="flat", borderwidth=0,
            cursor="hand2", padx=tema.px(20), pady=tema.px(10),
            activebackground=tema._ajustar_cor(tema.COR_SUCESSO, 0.85),
            activeforeground=tema.COR_TEXTO_CLARO,
        )
        self._botao_gerar.pack(side="right", padx=(0, tema.px(8)))

        self.bind("<Escape>", lambda e: self.destroy())

    def _opcao(self, pai, valor: str, titulo: str, detalhe: str, habilitado: bool = True) -> None:
        quadro = tk.Frame(pai, bg=tema.COR_CARD)
        quadro.pack(fill="x", pady=tema.px(4))

        botao = tk.Radiobutton(
            quadro, text=titulo, value=valor, variable=self._escolha,
            bg=tema.COR_CARD, fg=tema.COR_TEXTO, selectcolor=tema.COR_CARD,
            font=tema.fonte(13, forte=True), anchor="w",
            activebackground=tema.COR_CARD, cursor="hand2",
            state="normal" if habilitado else "disabled",
        )
        botao.pack(anchor="w")

        tk.Label(
            quadro, text=detalhe, bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(11),
        ).pack(anchor="w", padx=(tema.px(24), 0))

    @staticmethod
    def _paginas(quantidade: int) -> int:
        from . import cartoes
        por_pagina = cartoes.por_pagina()
        return max(1, (quantidade + por_pagina - 1) // por_pagina)

    def _centralizar(self) -> None:
        self.update_idletasks()
        pai = self.master.winfo_toplevel()
        x = pai.winfo_rootx() + (pai.winfo_width() - self.winfo_width()) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -----------------------------------------------------------------------
    # Geração
    # -----------------------------------------------------------------------
    def _gerar(self) -> None:
        if self._gerando:
            return

        selecionados = self._recentes if self._escolha.get() == "recentes" else self._todos
        if not selecionados:
            self._aviso.configure(text="Não há alunos para gerar.", fg=tema.COR_AVISO)
            return

        self._gerando = True
        self._botao_gerar.configure(state="disabled")
        self._aviso.configure(
            text=f"Gerando {len(selecionados)} cartões…", fg=tema.COR_TEXTO_SUAVE
        )
        # Fora da thread da interface: cento e vinte cartões levam quase um
        # segundo, e a janela não pode congelar no meio.
        threading.Thread(target=self._trabalhar, args=(selecionados,), daemon=True).start()

    def _trabalhar(self, selecionados: list[dict]) -> None:
        from . import cartoes

        carimbo = datetime.now().strftime("%Y-%m-%d-%H%M")
        destino = PASTA_SAIDA / f"cartoes-{carimbo}.pdf"
        try:
            cartoes.gerar_pdf(selecionados, destino)
        except Exception as erro:  # noqa: BLE001
            self.after(0, lambda: self._falhou(str(erro)))
            return
        self.after(0, lambda: self._pronto(destino, len(selecionados)))

    def _pronto(self, destino: Path, quantidade: int) -> None:
        self._gerando = False
        self._botao_gerar.configure(state="normal")
        self._aviso.configure(
            text=f"{quantidade} cartões em {self._paginas(quantidade)} páginas.\n{destino}",
            fg=tema.COR_SUCESSO,
        )
        try:
            _abrir_no_sistema(destino)
        except OSError as erro:
            self._aviso.configure(
                text=f"PDF salvo, mas não consegui abrir sozinho ({erro}).\n{destino}",
                fg=tema.COR_AVISO,
            )

    def _falhou(self, motivo: str) -> None:
        self._gerando = False
        self._botao_gerar.configure(state="normal")
        self._aviso.configure(text=f"Não foi possível gerar: {motivo}", fg=tema.COR_AVISO)


def abrir(pai: tk.Misc, base) -> None:
    DialogoCartoes(pai, base)
