"""
SIARRN — Diálogos do totem

Dois, e os dois são curtos de propósito: um acontece com a fila do almoço
parada atrás da pessoa, o outro com alguém da cozinha esperando.
"""
from __future__ import annotations

import tkinter as tk

from . import ui_formas as formas, ui_tema as tema

# O cadastro acontece com a fila parada atrás do aluno, numa tela lida de
# longe. Ficava em 17 contra os 30 da busca — pequeno demais para o lugar.
TAM_CAMPO = 22


class _DialogoBase(tk.Toplevel):
    """Janela modal no estilo do SIGBEF: faixa azul no topo, corpo branco."""

    def __init__(self, pai: tk.Misc, titulo: str, subtitulo: str) -> None:
        super().__init__(pai)
        self.resultado = None

        self.title("SIARRN")
        self.configure(bg=tema.COR_CARD)
        self.transient(pai.winfo_toplevel())
        self.resizable(False, False)

        cabecalho = tk.Frame(self, bg=tema.COR_PRIMARIA)
        cabecalho.pack(fill="x")
        tk.Label(
            cabecalho, text=titulo, bg=tema.COR_PRIMARIA, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(19, forte=True),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(16), 0))
        tk.Label(
            cabecalho, text=subtitulo, bg=tema.COR_PRIMARIA, fg=tema.COR_PRIMARIA_SUAVE,
            font=tema.fonte(12),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(2), tema.px(16)))

        self.corpo = tk.Frame(self, bg=tema.COR_CARD)
        self.corpo.pack(fill="both", expand=True, padx=tema.px(24), pady=tema.px(20))

        self.rodape = tk.Frame(self, bg=tema.COR_CARD)
        self.rodape.pack(fill="x", padx=tema.px(24), pady=(0, tema.px(20)))

    def _botao(self, texto: str, comando, cor: str,
               principal: bool = False) -> formas.BotaoArredondado:
        botao = formas.BotaoArredondado(
            self.rodape, text=texto, command=comando,
            bg=cor, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(13, forte=True),
            padx=tema.px(22), pady=tema.px(11),
        )
        botao.pack(side="right", padx=(tema.px(8), 0))
        if principal:
            self._principal = botao
        return botao

    def _centralizar_e_esperar(self) -> None:
        self.update_idletasks()
        pai = self.master.winfo_toplevel()
        x = pai.winfo_rootx() + (pai.winfo_width() - self.winfo_width()) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.grab_set()
        self.wait_window()

    def _cancelar(self) -> None:
        self.resultado = None
        self.destroy()


class DialogoCadastro(_DialogoBase):
    """Cadastro de aluno na própria fila, em dez segundos.

    Não existe carteirinha na escola e a secretaria não forneceu lista nenhuma:
    a base do sistema se constrói aqui, um aluno por vez, na primeira vez que
    cada um almoça. Por isso são só dois campos — qualquer coisa além disso
    vira fila parada.
    """

    def __init__(self, pai: tk.Misc, nome_sugerido: str = "") -> None:
        super().__init__(pai, "Primeiro almoço", "Vamos te cadastrar. Só acontece uma vez.")

        tk.Label(
            self.corpo, text="Nome completo", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(12),
        ).grid(row=0, column=0, sticky="w", pady=(0, tema.px(4)))

        self.campo_nome = tk.Entry(
            self.corpo, font=tema.fonte(TAM_CAMPO), width=24,
            relief="solid", borderwidth=1, highlightthickness=0,
            bg="white", fg=tema.COR_TEXTO, insertbackground=tema.COR_DESTAQUE,
        )
        self.campo_nome.grid(row=1, column=0, sticky="ew", ipady=tema.px(11))
        self.campo_nome.insert(0, nome_sugerido)

        tk.Label(
            self.corpo, text="Turma", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(12),
        ).grid(row=2, column=0, sticky="w", pady=(tema.px(14), tema.px(4)))

        self.campo_turma = tk.Entry(
            self.corpo, font=tema.fonte(TAM_CAMPO), width=24,
            relief="solid", borderwidth=1, highlightthickness=0,
            bg="white", fg=tema.COR_TEXTO, insertbackground=tema.COR_DESTAQUE,
        )
        self.campo_turma.grid(row=3, column=0, sticky="ew", ipady=tema.px(11))
        self.corpo.columnconfigure(0, weight=1)

        self._botao("Cadastrar e almoçar", self._confirmar, tema.COR_SUCESSO, principal=True)
        self._botao("Cancelar", self._cancelar, tema.COR_TEXTO_SUAVE)

        self.campo_nome.bind("<Return>", lambda e: self.campo_turma.focus_set())
        self.campo_turma.bind("<Return>", lambda e: self._confirmar())
        self.bind("<Escape>", lambda e: self._cancelar())

        self.campo_nome.focus_set()
        self._centralizar_e_esperar()

    def _confirmar(self) -> None:
        nome = self.campo_nome.get().strip()
        # Nome vazio não vira cadastro: um aluno sem nome é impossível de achar
        # depois e polui a base para sempre.
        if not nome:
            self.campo_nome.focus_set()
            return
        self.resultado = (nome, self.campo_turma.get().strip())
        self.destroy()


class DialogoPin(_DialogoBase):
    """Entrada do modo gestão."""

    def __init__(self, pai: tk.Misc, pin_esperado: str) -> None:
        super().__init__(pai, "Cozinha", "Digite o PIN de acesso.")
        self._pin_esperado = pin_esperado

        self.campo = tk.Entry(
            self.corpo, font=tema.fonte(22, forte=True), width=10, show="•",
            justify="center", relief="solid", borderwidth=1, highlightthickness=0,
            bg="white", fg=tema.COR_TEXTO, insertbackground=tema.COR_DESTAQUE,
        )
        self.campo.pack(ipady=tema.px(8))

        self._botao("Entrar", self._confirmar, tema.COR_PRIMARIA, principal=True)
        self._botao("Cancelar", self._cancelar, tema.COR_TEXTO_SUAVE)

        self.campo.bind("<Return>", lambda e: self._confirmar())
        self.bind("<Escape>", lambda e: self._cancelar())

        self.campo.focus_set()
        self._centralizar_e_esperar()

    def _confirmar(self) -> None:
        if self.campo.get().strip() == self._pin_esperado:
            self.resultado = True
            self.destroy()
        else:
            # Sem mensagem de erro: quem errou sabe que errou, e um aviso na tela
            # só ensinaria a um aluno curioso que ali existe algo a descobrir.
            self.campo.delete(0, "end")


def pedir_cadastro(pai: tk.Misc, nome_sugerido: str = "") -> tuple[str, str] | None:
    return DialogoCadastro(pai, nome_sugerido).resultado


def pedir_pin(pai: tk.Misc, pin_esperado: str) -> bool:
    return bool(DialogoPin(pai, pin_esperado).resultado)
