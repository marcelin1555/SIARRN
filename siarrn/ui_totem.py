"""
SIARRN — A tela da fila do almoço

Três regras governam tudo aqui:

1. **Se resolve a três metros.** Quem está na fila enxerga a tela de longe e
   precisa entender sem ler instrução: nome grande, cor ocupando tudo.
2. **Nunca espera o servidor.** A busca é local e o registro vai para a fila em
   disco. A confirmação aparece na hora, com ou sem rede.
3. **Ninguém vê vermelho.** O sistema não nega comida a aluno. Erro de rede é
   problema do totem, e o aluno não deveria nem perceber.
"""
from __future__ import annotations

import tkinter as tk

from . import ui_dialogos, ui_tema as tema
from .base_local import LIMITE_RESULTADOS
from .cliente_api import ErroDeRede

# Quanto tempo a confirmação fica na tela antes de liberar o próximo da fila.
MILISSEGUNDOS_CONFIRMACAO = 2200

# Três toques no rodapé abrem a gestão. A contagem zera depois disso para que
# cliques distraídos ao longo do almoço não somem até três por acidente.
MILISSEGUNDOS_TOQUE = 1500


class _LinhaAluno:
    """Uma linha da lista de resultados.

    As linhas são criadas uma vez e reaproveitadas a cada busca, em vez de
    destruídas e recriadas. Recriar vinte blocos de widgets a cada tecla
    digitada faz a lista piscar e engasgar — e quem está com pressa digita
    rápido.
    """

    def __init__(self, pai: tk.Misc, ao_escolher) -> None:
        self._aluno: dict | None = None
        self._ao_escolher = ao_escolher

        self.quadro = tk.Frame(
            pai, bg=tema.COR_CARD,
            highlightbackground=tema.COR_BORDA, highlightthickness=2,
            cursor="hand2",
        )
        self.nome = tk.Label(
            self.quadro, bg=tema.COR_CARD, fg=tema.COR_TEXTO,
            font=tema.fonte(tema.TAM_ALUNO, forte=True), anchor="w",
        )
        self.nome.pack(side="left", padx=(tema.px(22), 0), pady=tema.px(14))

        self.turma = tk.Label(
            self.quadro, bg=tema.COR_CARD, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_TURMA), anchor="e",
        )
        self.turma.pack(side="right", padx=(0, tema.px(22)))

        # O clique precisa valer no quadro e nos rótulos: um dedo na fila acerta
        # o texto, não a borda.
        for alvo in (self.quadro, self.nome, self.turma):
            alvo.bind("<Button-1>", self._clicar)
            alvo.bind("<Enter>", self._entrar)
            alvo.bind("<Leave>", self._sair)

    def _clicar(self, _evento=None) -> None:
        if self._aluno is not None:
            self._ao_escolher(self._aluno)

    def _pintar(self, cor: str) -> None:
        for alvo in (self.quadro, self.nome, self.turma):
            alvo.configure(bg=cor)

    def _entrar(self, _evento=None) -> None:
        self._pintar(tema.COR_HOVER_CARD)

    def _sair(self, _evento=None) -> None:
        self._pintar(tema.COR_CARD)

    def mostrar(self, aluno: dict) -> None:
        self._aluno = aluno
        self.nome.configure(text=aluno.get("nome", ""))
        self.turma.configure(text=aluno.get("turma", "") or "")
        self._pintar(tema.COR_CARD)
        self.quadro.pack(fill="x", pady=(0, tema.px(8)))

    def esconder(self) -> None:
        self._aluno = None
        self.quadro.pack_forget()

    @property
    def aluno(self) -> dict | None:
        return self._aluno


class TelaTotem(tk.Frame):
    def __init__(self, master, base, fila, cliente, ao_pedir_gestao) -> None:
        super().__init__(master, bg=tema.COR_FUNDO)
        self._base = base
        self._fila = fila
        self._cliente = cliente
        self._ao_pedir_gestao = ao_pedir_gestao

        self._toques = 0
        self._retorno_agendado = None

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._painel_busca = tk.Frame(self, bg=tema.COR_FUNDO)
        self._painel_confirmacao = tk.Frame(self, bg=tema.COR_SUCESSO)
        for painel in (self._painel_busca, self._painel_confirmacao):
            painel.grid(row=0, column=0, sticky="nsew")

        self._montar_busca()
        self._montar_confirmacao()
        self.mostrar_busca()

    # -----------------------------------------------------------------------
    # Tela de busca
    # -----------------------------------------------------------------------
    def _montar_busca(self) -> None:
        cabecalho = tk.Frame(self._painel_busca, bg=tema.COR_PRIMARIA)
        cabecalho.pack(fill="x")
        tk.Label(
            cabecalho, text="Digite seu nome",
            bg=tema.COR_PRIMARIA, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_CABECALHO, forte=True),
        ).pack(pady=(tema.px(22), 0))
        tk.Label(
            cabecalho, text="Depois toque no seu nome para registrar o almoço",
            bg=tema.COR_PRIMARIA, fg=tema.COR_PRIMARIA_SUAVE,
            font=tema.fonte(tema.TAM_CABECALHO_SUB),
        ).pack(pady=(tema.px(4), tema.px(22)))

        corpo = tk.Frame(self._painel_busca, bg=tema.COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=tema.px(46), pady=tema.px(26))

        self._campo = tk.Entry(
            corpo, font=tema.fonte(tema.TAM_BUSCA, forte=True),
            relief="solid", borderwidth=2, highlightthickness=0,
            bg=tema.COR_CARD, fg=tema.COR_TEXTO,
            insertbackground=tema.COR_DESTAQUE,  # o cursor é o único âmbar da tela
            insertwidth=tema.px(3),
        )
        self._campo.pack(fill="x", ipady=tema.px(13))
        self._campo.bind("<KeyRelease>", self._ao_digitar)
        self._campo.bind("<Return>", self._escolher_primeiro)
        self._campo.bind("<Down>", self._escolher_primeiro)

        self._lista = tk.Frame(corpo, bg=tema.COR_FUNDO)
        self._lista.pack(fill="both", expand=True, pady=(tema.px(18), 0))

        self._linhas = [_LinhaAluno(self._lista, self._registrar) for _ in range(LIMITE_RESULTADOS)]

        self._dica = tk.Label(
            self._lista, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_TURMA),
        )

        self._montar_rodape()

    def _montar_rodape(self) -> None:
        rodape = tk.Frame(self._painel_busca, bg=tema.COR_FUNDO,
                          highlightbackground=tema.COR_BORDA, highlightthickness=1)
        rodape.pack(fill="x", side="bottom")

        self._status = tk.Label(
            rodape, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_RODAPE),
        )
        self._status.pack(side="left", padx=tema.px(26), pady=tema.px(12))
        # Atalho discreto para a cozinha. Nada na tela sugere que o rodapé é
        # clicável, então um aluno curioso não descobre por acidente.
        self._status.bind("<Button-1>", self._contar_toque)

        botao = tk.Button(
            rodape, text="Não encontrei meu nome", command=self._abrir_cadastro,
            bg=tema.COR_SECUNDARIA, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(13, forte=True), relief="flat", borderwidth=0,
            cursor="hand2", padx=tema.px(18), pady=tema.px(9),
            activebackground=tema._ajustar_cor(tema.COR_SECUNDARIA, 0.85),
            activeforeground=tema.COR_TEXTO_CLARO,
        )
        botao.pack(side="right", padx=tema.px(20), pady=tema.px(9))

    # -----------------------------------------------------------------------
    # Tela de confirmação
    # -----------------------------------------------------------------------
    def _montar_confirmacao(self) -> None:
        centro = tk.Frame(self._painel_confirmacao, bg=tema.COR_SUCESSO)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        self._nome_confirmado = tk.Label(
            centro, bg=tema.COR_SUCESSO, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_NOME_CONFIRMADO, forte=True),
            wraplength=tema.px(1100), justify="center",
        )
        self._nome_confirmado.pack()

        # A única pincelada de âmbar da tela verde.
        tk.Frame(centro, bg=tema.COR_DESTAQUE, height=tema.px(5), width=tema.px(120)).pack(
            pady=tema.px(20)
        )

        self._mensagem = tk.Label(
            centro, bg=tema.COR_SUCESSO, fg=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_MENSAGEM),
        )
        self._mensagem.pack()

        self._turma_confirmada = tk.Label(
            centro, bg=tema.COR_SUCESSO, fg=tema.COR_SUCESSO_SUAVE,
            font=tema.fonte(tema.TAM_TURMA),
        )
        self._turma_confirmada.pack(pady=(tema.px(10), 0))

    # -----------------------------------------------------------------------
    # Comportamento
    # -----------------------------------------------------------------------
    def _ao_digitar(self, _evento=None) -> None:
        encontrados = self._base.buscar(self._campo.get())

        for linha, aluno in zip(self._linhas, encontrados):
            linha.mostrar(aluno)
        for linha in self._linhas[len(encontrados):]:
            linha.esconder()

        digitado = self._campo.get().strip()
        if digitado and len(digitado) >= 2 and not encontrados:
            self._dica.configure(
                text='Nenhum nome encontrado. Toque em "Não encontrei meu nome" abaixo.'
            )
            self._dica.pack(pady=tema.px(20))
        else:
            self._dica.pack_forget()

    def _escolher_primeiro(self, _evento=None) -> str:
        """Enter registra o primeiro da lista — atalho de quem já sabe usar."""
        for linha in self._linhas:
            if linha.aluno is not None:
                self._registrar(linha.aluno)
                break
        return "break"

    def _registrar(self, aluno: dict) -> None:
        # Grava em disco e confirma na hora. Enviar ao servidor é problema da
        # thread de sincronização, não de quem está com o prato na mão.
        self._fila.registrar(aluno, "nome")
        self._confirmar(aluno.get("nome", ""), "Bom almoço!", aluno.get("turma", ""))

    def _confirmar(self, nome: str, mensagem: str, turma: str = "") -> None:
        self._nome_confirmado.configure(text=nome)
        self._mensagem.configure(text=mensagem)
        self._turma_confirmada.configure(text=turma or "")

        self._painel_confirmacao.tkraise()

        if self._retorno_agendado is not None:
            self.after_cancel(self._retorno_agendado)
        self._retorno_agendado = self.after(MILISSEGUNDOS_CONFIRMACAO, self.mostrar_busca)

    def mostrar_busca(self) -> None:
        self._retorno_agendado = None
        self._campo.delete(0, "end")
        for linha in self._linhas:
            linha.esconder()
        self._dica.pack_forget()
        self.atualizar_status()
        self._painel_busca.tkraise()
        self._campo.focus_set()

    def _abrir_cadastro(self) -> None:
        sugestao = self._campo.get().strip()
        dados_novos = ui_dialogos.pedir_cadastro(self, sugestao)
        if dados_novos is None:
            self._campo.focus_set()
            return

        nome, turma = dados_novos
        criado = self._cadastrar_no_servidor(nome, turma)

        if criado is not None:
            self._base.acrescentar(criado)
            self._fila.registrar(criado, "nome")
        else:
            # Servidor fora: guarda o cadastro junto com o almoço e resolve os
            # dois na sincronização. O aluno não pode ficar sem comer porque a
            # rede caiu.
            self._fila.registrar_cadastro_pendente(nome, turma)

        self._confirmar(nome, "Cadastrado. Bom almoço!", turma)

    def _cadastrar_no_servidor(self, nome: str, turma: str) -> dict | None:
        try:
            return self._cliente.cadastrar(nome, turma)
        except ErroDeRede:
            return None

    # -----------------------------------------------------------------------
    # Rodapé e atalho da gestão
    # -----------------------------------------------------------------------
    def atualizar_status(self) -> None:
        """Estado do equipamento, em letra pequena: informação para a escola."""
        pendentes = self._fila.pendentes()
        if pendentes == 0:
            situacao = "tudo sincronizado"
        elif pendentes == 1:
            situacao = "1 almoço a enviar"
        else:
            situacao = f"{pendentes} almoços a enviar"

        self._status.configure(text=f"{self._base.tamanho()} alunos  ·  {situacao}")

    def _contar_toque(self, _evento=None) -> None:
        self._toques += 1
        if self._toques >= 3:
            self._toques = 0
            self._ao_pedir_gestao()
            return
        self.after(MILISSEGUNDOS_TOQUE, self._zerar_toques)

    def _zerar_toques(self) -> None:
        self._toques = 0
