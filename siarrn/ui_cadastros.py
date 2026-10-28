"""
SIARRN — Correção de cadastros, no modo gestão

O cadastro é feito pelo próprio aluno, na fila, com pressa. Isso gera duas
coisas: nome digitado errado, que some da busca, e o mesmo aluno cadastrado
duas vezes, porque não se achou e tocou em "não encontrei meu nome".

A duplicata é a pior das duas. O registro abandonado continua entrando na
previsão pelo hábito antigo por quatro semanas — cerca de um prato a mais por
duplicata, no sistema que existe para reduzir sobra.

Juntar e renomear precisam do servidor: a correção vale para todos os totens e
para o celular do aluno, e não faz sentido ficar guardada só nesta máquina.
"""
from __future__ import annotations

import threading
import tkinter as tk

from . import texto, ui_dialogos, ui_formas as formas, ui_tema as tema
from .cliente_api import ErroDeRede

# Uma janela que cabe na tela, sem rolagem. Depois de juntar um par, o próximo
# sobe — quem corrige trabalha de cima para baixo.
PARES_VISIVEIS = 4
RESULTADOS_BUSCA = 5


def _desde(aluno: dict) -> str:
    """"desde 03/08", a partir do criado_em do servidor."""
    data = (aluno.get("criado_em") or "")[:10]
    if len(data) != 10:
        return ""
    return f"desde {data[8:10]}/{data[5:7]}"


def _detalhe(aluno: dict) -> str:
    partes = [aluno.get("turma") or "sem turma", _desde(aluno)]
    return " · ".join(p for p in partes if p)


class DialogoCadastros(tk.Toplevel):
    def __init__(self, pai: tk.Misc, cliente, base) -> None:
        super().__init__(pai)
        self._cliente = cliente
        self._base = base
        self._ocupado = False

        self.title("SIARRN")
        self.configure(bg=tema.COR_CARD)
        self.transient(pai.winfo_toplevel())
        self.resizable(False, False)

        self._montar()
        self._mostrar_pares()
        self._centralizar()
        self.grab_set()

    # -----------------------------------------------------------------------
    # Montagem
    # -----------------------------------------------------------------------
    def _montar(self) -> None:
        cabecalho = tk.Frame(self, bg=tema.COR_PRIMARIA)
        cabecalho.pack(fill="x")
        tk.Label(
            cabecalho, text="Corrigir cadastros", bg=tema.COR_PRIMARIA,
            fg=tema.COR_TEXTO_CLARO, font=tema.fonte(19, forte=True),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(16), 0))
        tk.Label(
            cabecalho, text="Nomes errados e alunos cadastrados duas vezes.",
            bg=tema.COR_PRIMARIA, fg=tema.COR_PRIMARIA_SUAVE, font=tema.fonte(12),
        ).pack(anchor="w", padx=tema.px(24), pady=(tema.px(2), tema.px(16)))

        corpo = tk.Frame(self, bg=tema.COR_CARD)
        corpo.pack(fill="both", expand=True, padx=tema.px(24), pady=tema.px(18))

        tk.Label(
            corpo, text="Podem ser a mesma pessoa", bg=tema.COR_CARD,
            fg=tema.COR_TEXTO, font=tema.fonte(14, forte=True),
        ).pack(anchor="w")
        self._resumo_pares = tk.Label(
            corpo, bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE, font=tema.fonte(11),
            wraplength=tema.px(620), justify="left",
        )
        self._resumo_pares.pack(anchor="w", pady=(0, tema.px(8)))
        self._lista_pares = tk.Frame(corpo, bg=tema.COR_CARD)
        self._lista_pares.pack(fill="x")

        tk.Frame(corpo, bg=tema.COR_BORDA, height=1).pack(fill="x", pady=tema.px(16))

        tk.Label(
            corpo, text="Corrigir um nome", bg=tema.COR_CARD,
            fg=tema.COR_TEXTO, font=tema.fonte(14, forte=True),
        ).pack(anchor="w", pady=(0, tema.px(6)))
        self._busca = tk.Entry(
            corpo, font=tema.fonte(15), relief="solid", borderwidth=1,
            highlightthickness=0, bg="white", fg=tema.COR_TEXTO,
            insertbackground=tema.COR_DESTAQUE,
        )
        self._busca.pack(fill="x", ipady=tema.px(7))
        self._busca.bind("<KeyRelease>", lambda e: self._mostrar_busca())
        self._lista_busca = tk.Frame(corpo, bg=tema.COR_CARD)
        self._lista_busca.pack(fill="x", pady=(tema.px(6), 0))

        self._aviso = tk.Label(
            corpo, text="", bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(11), wraplength=tema.px(620), justify="left",
        )
        self._aviso.pack(anchor="w", pady=(tema.px(12), 0))

        rodape = tk.Frame(self, bg=tema.COR_CARD)
        rodape.pack(fill="x", padx=tema.px(24), pady=(0, tema.px(20)))
        formas.BotaoArredondado(
            rodape, text="Fechar", command=self.destroy, bg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(13, forte=True), padx=tema.px(18), pady=tema.px(10),
        ).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())

    def _mostrar_pares(self) -> None:
        for filho in self._lista_pares.winfo_children():
            filho.destroy()

        pares = texto.pares_suspeitos(self._base.amostra(10_000))
        if not pares:
            self._resumo_pares.configure(text="Nenhum par parecido. Nada a juntar por enquanto.")
            return

        visiveis = pares[:PARES_VISIVEIS]
        restante = f" Mostrando {len(visiveis)} de {len(pares)}." if len(pares) > len(visiveis) else ""
        self._resumo_pares.configure(
            text="Confira a turma antes: irmãos e primos também têm nomes parecidos."
            + restante
        )
        for a, b in visiveis:
            self._linha_par(a, b)

    def _linha_par(self, a: dict, b: dict) -> None:
        linha = tk.Frame(self._lista_pares, bg=tema.COR_FUNDO)
        linha.pack(fill="x", pady=tema.px(3))
        for coluna, (este, outro) in enumerate(((a, b), (b, a))):
            celula = tk.Frame(linha, bg=tema.COR_FUNDO)
            celula.grid(row=0, column=coluna, sticky="nsew",
                        padx=tema.px(12), pady=tema.px(8))
            tk.Label(
                celula, text=este.get("nome", ""), bg=tema.COR_FUNDO, fg=tema.COR_TEXTO,
                font=tema.fonte(13, forte=True), anchor="w",
            ).pack(anchor="w")
            tk.Label(
                celula, text=_detalhe(este), bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
                font=tema.fonte(11), anchor="w",
            ).pack(anchor="w")
            formas.BotaoArredondado(
                celula, text="Ficar com este nome", bg=tema.COR_SECUNDARIA,
                font=tema.fonte(11, forte=True), padx=tema.px(12), pady=tema.px(6),
                command=lambda m=este, d=outro: self._juntar(m, d),
            ).pack(anchor="w", pady=(tema.px(6), 0))
        linha.columnconfigure((0, 1), weight=1, uniform="par")

    def _mostrar_busca(self) -> None:
        for filho in self._lista_busca.winfo_children():
            filho.destroy()
        for aluno in self._base.buscar(self._busca.get())[:RESULTADOS_BUSCA]:
            linha = tk.Frame(self._lista_busca, bg=tema.COR_CARD)
            linha.pack(fill="x", pady=tema.px(2))
            formas.BotaoArredondado(
                linha, text="Corrigir", bg=tema.COR_SECUNDARIA,
                font=tema.fonte(11, forte=True), padx=tema.px(12), pady=tema.px(5),
                command=lambda a=aluno: self._renomear(a),
            ).pack(side="right")
            tk.Label(
                linha, text=f"{aluno.get('nome', '')}   ", bg=tema.COR_CARD,
                fg=tema.COR_TEXTO, font=tema.fonte(13),
            ).pack(side="left")
            tk.Label(
                linha, text=_detalhe(aluno), bg=tema.COR_CARD,
                fg=tema.COR_TEXTO_SUAVE, font=tema.fonte(11),
            ).pack(side="left")

    def _centralizar(self) -> None:
        self.update_idletasks()
        pai = self.master.winfo_toplevel()
        x = pai.winfo_rootx() + (pai.winfo_width() - self.winfo_width()) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - self.winfo_height()) // 4
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -----------------------------------------------------------------------
    # Ações
    # -----------------------------------------------------------------------
    def _juntar(self, manter: dict, descartar: dict) -> None:
        if self._ocupado:
            return
        pergunta = (
            f"«{manter['nome']}» e «{descartar['nome']}» passam a ser um aluno só, "
            f"com o nome «{manter['nome']}». Os almoços dos dois ficam juntos, "
            "e os dois cartões continuam valendo."
        )
        if ui_dialogos.confirmar(self, "Mesma pessoa?", pergunta, "Juntar"):
            self._executar(lambda: self._cliente.mesclar(manter["id"], descartar["id"]),
                           f"Juntado em «{manter['nome']}».")

    def _renomear(self, aluno: dict) -> None:
        if self._ocupado:
            return
        novo = ui_dialogos.pedir_correcao(self, aluno.get("nome", ""), aluno.get("turma") or "")
        if novo:
            nome, turma = novo
            self._executar(lambda: self._cliente.renomear(aluno["id"], nome, turma),
                           f"Agora é «{nome}».")

    def _executar(self, acao, mensagem: str) -> None:
        self._ocupado = True
        self._aviso.configure(text="Enviando ao servidor…", fg=tema.COR_TEXTO_SUAVE)

        def trabalhar() -> None:
            try:
                acao()
            except ErroDeRede as erro:
                self.after(0, lambda: self._falhou(str(erro)))
                return
            # A cópia local precisa saber da correção já, ou o par juntado
            # continuaria na lista e o nome antigo na busca da fila.
            self._base.atualizar(self._cliente)
            self.after(0, lambda: self._pronto(mensagem))

        threading.Thread(target=trabalhar, daemon=True).start()

    def _pronto(self, mensagem: str) -> None:
        self._ocupado = False
        self._aviso.configure(text=mensagem, fg=tema.COR_SUCESSO)
        self._mostrar_pares()
        self._mostrar_busca()

    def _falhou(self, motivo: str) -> None:
        self._ocupado = False
        self._aviso.configure(
            text=f"Não foi possível corrigir: {motivo}. A correção precisa do servidor no ar.",
            fg=tema.COR_AVISO,
        )


def abrir(pai: tk.Misc, cliente, base) -> None:
    DialogoCadastros(pai, cliente, base)
