"""
SIARRN — A tela da fila do almoço

Três regras governam tudo aqui:

1. **Se resolve a três metros.** Quem está na fila enxerga a tela de longe e
   precisa entender sem ler instrução: nome grande, cor ocupando tudo.
2. **Nunca espera o servidor.** A busca é local e o registro vai para a fila em
   disco. A confirmação aparece na hora, com ou sem rede.
3. **Ninguém vê vermelho.** O sistema não nega comida a aluno. Erro de rede é
   problema do totem, e o aluno não deveria nem perceber.

A forma vem da tela de apresentação: faixa em degradê no topo, campo de busca
num cartão flutuando sobre ela, nomes em cartões de cantos arredondados. O
corpo, porém, fica claro de propósito — são até vinte nomes lidos em sequência
num refeitório com luz de janela, e fundo escuro com cartão branco seria
dramático e pior de ler.
"""
from __future__ import annotations

import threading
import tkinter as tk

from . import ui_dialogos, ui_formas as formas, ui_tema as tema
from .base_local import LIMITE_RESULTADOS
from .cliente_api import ErroDeRede

# Quanto tempo a confirmação fica na tela antes de liberar o próximo da fila.
MILISSEGUNDOS_CONFIRMACAO = 2200

# Três toques no rodapé abrem a gestão. A contagem zera depois disso para que
# cliques distraídos ao longo do almoço não somem até três por acidente.
MILISSEGUNDOS_TOQUE = 1500

# O cardápio da faixa superior é buscado de vez em quando, sem pressa: ele muda
# uma vez por dia, e quem está na fila não está esperando por ele.
MILISSEGUNDOS_CARDAPIO = 120_000

ALTURA_LINHA = 62        # altura de cada cartão de nome, antes da escala
ESPACO_LINHA = 10

# A faixa do topo. Alta o bastante para o degradê se ler como degradê e
# para o cartão do campo caber apoiado nela.
ALTURA_FAIXA = 272


class _ListaDeNomes(tk.Canvas):
    """A lista de resultados, desenhada em Canvas.

    O Tkinter não arredonda `Frame`, então cartões arredondados precisam ser
    desenhados. A regra que governava a versão em widgets continua valendo e é
    a razão de esta classe existir em vez de um laço que redesenha tudo: os
    itens são criados **uma vez**, na montagem, e a cada busca apenas mudam de
    texto e de posição. Recriar vinte cartões a cada tecla digitada faz a lista
    piscar e engasgar — e quem está com pressa digita rápido.

    Um ganho sobre a versão anterior: o alvo do toque passa a ser o cartão
    inteiro por uma tag só. Antes era preciso ligar três widgets separados
    (quadro, nome e turma) para que o dedo acertasse o texto e não só a borda.
    """

    def __init__(self, pai: tk.Misc, ao_escolher) -> None:
        super().__init__(pai, bg=tema.COR_FUNDO, highlightthickness=0)
        self._ao_escolher = ao_escolher
        self._alunos: list[dict | None] = [None] * LIMITE_RESULTADOS
        self._grupos: list[dict] = []
        self._largura = 0
        self._altura = 0
        self.truncada = False

        for indice in range(LIMITE_RESULTADOS):
            self._grupos.append(self._criar_grupo(indice))

        self.bind("<Configure>", self._ao_redimensionar)

    def _criar_grupo(self, indice: int) -> dict:
        """Um cartão: fundo arredondado, nome à esquerda, turma à direita."""
        tag = f"linha{indice}"
        altura = tema.px(ALTURA_LINHA)

        fundo = formas.bloco_arredondado(
            self, 0, 0, 10, altura, tema.px(tema.RAIO_CANTO_PEQUENO),
            tema.COR_CARD, (tag, "cartao"),
        )
        nome = self.create_text(
            0, 0, text="", anchor="w", fill=tema.COR_TEXTO,
            font=tema.fonte(tema.TAM_ALUNO, forte=True), tags=(tag, "cartao"),
        )
        turma = self.create_text(
            0, 0, text="", anchor="e", fill=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_TURMA), tags=(tag, "cartao"),
        )

        self.tag_bind(tag, "<Button-1>", lambda e, i=indice: self._clicar(i))
        self.tag_bind(tag, "<Enter>", lambda e, i=indice: self._pintar(i, tema.COR_HOVER_CARD))
        self.tag_bind(tag, "<Leave>", lambda e, i=indice: self._pintar(i, tema.COR_CARD))

        grupo = {"tag": tag, "fundo": fundo, "nome": nome, "turma": turma}
        self._esconder(grupo)
        return grupo

    def _esconder(self, grupo: dict) -> None:
        # Fora da área visível, em vez de destruído. Um `itemconfigure` de
        # estado seria mais explícito, mas mover é o que mantém os ids vivos
        # com uma chamada só.
        self.itemconfigure(grupo["tag"], state="hidden")

    def _clicar(self, indice: int) -> None:
        aluno = self._alunos[indice]
        if aluno is not None:
            self._ao_escolher(aluno)

    def _pintar(self, indice: int, cor: str) -> None:
        if self._alunos[indice] is None:
            return
        for item in self._grupos[indice]["fundo"]:
            self.itemconfigure(item, fill=cor)

    def _ao_redimensionar(self, evento) -> None:
        if (evento.width, evento.height) == (self._largura, self._altura):
            return
        self._largura, self._altura = evento.width, evento.height
        self._reposicionar()

    def mostrar(self, encontrados: list[dict]) -> None:
        self._alunos = [
            encontrados[i] if i < len(encontrados) else None
            for i in range(LIMITE_RESULTADOS)
        ]
        self._reposicionar()

    def _reposicionar(self) -> None:
        largura = self._largura or self.winfo_width()
        if largura <= 1:
            return

        altura = tema.px(ALTURA_LINHA)
        passo = altura + tema.px(ESPACO_LINHA)
        margem = tema.px(20)
        raio = tema.px(tema.RAIO_CANTO_PEQUENO)

        # Só entram os nomes que cabem **inteiros**. Um nome cortado ao meio
        # pela borda é pior que nome nenhum: de três metros ele parece defeito,
        # e quem procurava o próprio nome não sabe se devia rolar a tela — num
        # totem, não devia, porque não há como rolar.
        disponivel = self._altura or self.winfo_height()
        cabem = max(1, int(disponivel // passo)) if disponivel > 1 else LIMITE_RESULTADOS
        visiveis = sum(1 for aluno in self._alunos if aluno is not None)
        self.truncada = visiveis > cabem

        for indice, (grupo, aluno) in enumerate(zip(self._grupos, self._alunos)):
            if aluno is None or indice >= cabem:
                self._esconder(grupo)
                continue

            topo = indice * passo
            self.itemconfigure(grupo["tag"], state="normal")

            # Os seis itens do fundo precisam ser recolocados um a um: o
            # Canvas não tem "mover o grupo para estas coordenadas".
            self._mover_fundo(grupo["fundo"], 0, topo, largura, topo + altura, raio)

            self.coords(grupo["nome"], margem, topo + altura / 2)
            self.itemconfigure(grupo["nome"], text=aluno.get("nome", ""), fill=tema.COR_TEXTO)

            self.coords(grupo["turma"], largura - margem, topo + altura / 2)
            self.itemconfigure(grupo["turma"], text=aluno.get("turma", "") or "")

            self._pintar(indice, tema.COR_CARD)

    def _mover_fundo(self, ids: list[int], x1, y1, x2, y2, raio) -> None:
        raio = max(0, min(raio, (x2 - x1) / 2, (y2 - y1) / 2))
        diametro = raio * 2
        self.coords(ids[0], x1 + raio, y1, x2 - raio, y2)
        self.coords(ids[1], x1, y1 + raio, x2, y2 - raio)
        cantos = ((x1, y1), (x2 - diametro, y1),
                  (x1, y2 - diametro), (x2 - diametro, y2 - diametro))
        for item, (cx, cy) in zip(ids[2:], cantos):
            self.coords(item, cx, cy, cx + diametro, cy + diametro)

    @property
    def primeiro(self) -> dict | None:
        return self._alunos[0]


class TelaTotem(tk.Frame):
    def __init__(self, master, base, fila, cliente, ao_pedir_gestao) -> None:
        super().__init__(master, bg=tema.COR_FUNDO)
        self._base = base
        self._fila = fila
        self._cliente = cliente
        self._ao_pedir_gestao = ao_pedir_gestao

        self._toques = 0
        self._retorno_agendado = None
        self._agendamento_cardapio = None
        self._cartao_ativo = False
        self._cardapio = ""
        self._fundo_confirmacao = None
        self._tamanho_confirmacao = (0, 0)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._painel_busca = tk.Frame(self, bg=tema.COR_FUNDO)
        self._painel_confirmacao = tk.Canvas(
            self, bg=tema.COR_SUCESSO, highlightthickness=0
        )
        for painel in (self._painel_busca, self._painel_confirmacao):
            painel.grid(row=0, column=0, sticky="nsew")

        self._montar_busca()
        self._montar_confirmacao()
        self.mostrar_busca()
        self._buscar_cardapio()

    # -----------------------------------------------------------------------
    # Tela de busca
    # -----------------------------------------------------------------------
    def _montar_busca(self) -> None:
        self._faixa = formas.FaixaGradiente(self._painel_busca, altura=tema.px(ALTURA_FAIXA))
        self._faixa.pack(fill="x")
        self._faixa.bind("<Configure>", self._desenhar_faixa, add="+")

        self._montar_campo(self._faixa)

        # O rodapé vem antes do corpo de propósito: o `pack` atende os widgets
        # na ordem do código, e um corpo com `expand=True` declarado primeiro
        # consome o que sobra e deixa a barra de baixo sem espaço nenhum.
        self._montar_rodape()

        corpo = tk.Frame(self._painel_busca, bg=tema.COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=tema.px(46))

        self._dica_cartao = tk.Label(
            corpo, text="", bg=tema.COR_FUNDO, fg=tema.COR_SECUNDARIA,
            font=tema.fonte(tema.TAM_TURMA),
        )
        self._dica_cartao.pack(pady=(tema.px(16), 0))

        self._lista = _ListaDeNomes(corpo, self._registrar)
        self._lista.pack(fill="both", expand=True, pady=(tema.px(12), 0))

        self._dica = tk.Label(
            corpo, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_TURMA),
        )

    def _desenhar_faixa(self, _evento=None) -> None:
        """O texto do cabeçalho, desenhado sobre o degradê.

        Itens de Canvas, não Labels: um Label azul cobriria o degradê com cor
        chapada. É a mesma razão pela qual a tela de apresentação desenha todo
        o seu texto.
        """
        self._faixa.delete("texto")
        largura = self._faixa.winfo_width()
        if largura <= 1:
            return
        meio = largura / 2

        self._faixa.create_text(
            meio, tema.px(46), text="Digite seu nome", fill=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_CABECALHO, forte=True), tags="texto",
        )
        self._faixa.create_text(
            meio, tema.px(86), text="Depois toque no seu nome para registrar o almoço",
            fill=tema.COR_PRIMARIA_SUAVE,
            font=tema.fonte(tema.TAM_CABECALHO_SUB), tags="texto",
        )
        if self._cardapio:
            # O cardápio em letra pequena: quem entrou direto no toque não viu a
            # apresentação e perderia a informação até o totem voltar sozinho.
            self._faixa.create_text(
                meio, tema.px(122), text=f"HOJE: {self._cardapio.upper()}",
                fill=tema.COR_DESTAQUE, width=largura - tema.px(120), justify="center",
                font=tema.fonte(tema.TAM_CARDAPIO_FAIXA, forte=True), tags="texto",
            )

        self._faixa.coords("campo", tema.px(46), tema.px(ALTURA_FAIXA) - tema.px(24))
        self._faixa.itemconfigure("campo", width=largura - tema.px(92))

    def _montar_campo(self, faixa) -> None:
        """O campo de busca, num cartão branco apoiado na base da faixa azul.

        Branco com contorno âmbar sobre o degradê: é a única coisa que a pessoa
        precisa fazer, e precisa se destacar de tudo o mais. Entra por
        `create_window` porque um campo de digitação tem que ser widget de
        verdade — e, tendo cor própria, não precisa deixar o fundo passar.
        """
        cartao = tk.Frame(
            faixa, bg=tema.COR_DESTAQUE, padx=tema.px(3), pady=tema.px(3),
        )

        self._campo = tk.Entry(
            cartao, font=tema.fonte(tema.TAM_BUSCA, forte=True),
            relief="flat", borderwidth=0, highlightthickness=0,
            bg=tema.COR_CARD, fg=tema.COR_TEXTO,
            insertbackground=tema.COR_DESTAQUE,
            insertwidth=tema.px(3),
        )
        self._campo.pack(fill="x", ipady=tema.px(14), padx=tema.px(16))
        self._campo.bind("<KeyRelease>", self._ao_digitar)
        self._campo.bind("<Return>", self._escolher_primeiro)
        self._campo.bind("<Down>", self._escolher_primeiro)

        faixa.create_window(0, 0, window=cartao, anchor="sw", tags="campo")

    def _montar_rodape(self) -> None:
        rodape = tk.Frame(self._painel_busca, bg=tema.COR_FUNDO)
        rodape.pack(fill="x", side="bottom")

        self._status = tk.Label(
            rodape, bg=tema.COR_FUNDO, fg=tema.COR_TEXTO_SUAVE,
            font=tema.fonte(tema.TAM_RODAPE),
        )
        self._status.pack(side="left", padx=tema.px(46), pady=tema.px(16))
        # Atalho discreto para a cozinha. Nada na tela sugere que o rodapé é
        # clicável, então um aluno curioso não descobre por acidente.
        self._status.bind("<Button-1>", self._contar_toque)

        formas.BotaoArredondado(
            rodape, text="Não encontrei meu nome", command=self._abrir_cadastro,
            bg=tema.COR_SECUNDARIA, font=tema.fonte(13, forte=True),
            padx=tema.px(20), pady=tema.px(11),
        ).pack(side="right", padx=tema.px(46), pady=tema.px(10))

    # -----------------------------------------------------------------------
    # Tela de confirmação
    # -----------------------------------------------------------------------
    def _montar_confirmacao(self) -> None:
        """A tela verde, desenhada sobre um degradê.

        Tudo aqui é item de Canvas pela mesma razão da faixa da busca: um
        `Label` verde cobriria o degradê com um retângulo de cor chapada, e o
        quadro apareceria recortado no meio da tela.
        """
        self._nome = ""
        self._mensagem_texto = ""
        self._turma = ""
        self._painel_confirmacao.bind("<Configure>", self._pintar_confirmacao)

    def _pintar_confirmacao(self, _evento=None) -> None:
        tela = self._painel_confirmacao
        largura, altura = tela.winfo_width(), tela.winfo_height()
        if largura <= 1 or altura <= 1:
            return

        self._desenhar_fundo_confirmacao(largura, altura)

        tela.delete("texto")
        meio = largura / 2
        margem = largura - tema.px(80)

        # Dois passos: empilhar a partir do topo e só então centralizar o
        # conjunto. Reservar alturas fixas não funciona — um nome comprido
        # quebra em duas linhas e estoura a reserva, e a régua âmbar acaba
        # atravessando o nome. Aqui cada item é medido depois de desenhado,
        # com `anchor="n"` para que a coordenada seja o topo e não o centro.
        y = 0.0

        def empilhar(item: int, folga: int) -> None:
            nonlocal y
            y = tela.bbox(item)[3] + tema.px(folga)

        empilhar(tela.create_text(
            meio, y, text=self._nome, fill=tema.COR_TEXTO_CLARO, anchor="n",
            font=tema.fonte(tema.TAM_NOME_CONFIRMADO, forte=True),
            width=margem, justify="center", tags="texto",
        ), 26)

        # A única pincelada de âmbar da tela verde.
        empilhar(tela.create_rectangle(
            meio - tema.px(60), y, meio + tema.px(60), y + tema.px(5),
            fill=tema.COR_DESTAQUE, outline="", tags="texto",
        ), 24)

        empilhar(tela.create_text(
            meio, y, text=self._mensagem_texto, fill=tema.COR_TEXTO_CLARO,
            anchor="n", font=tema.fonte(tema.TAM_MENSAGEM), tags="texto",
        ), 18)

        if self._cardapio:
            empilhar(tela.create_text(
                meio, y, text=self._cardapio, fill=tema.COR_TEXTO_CLARO,
                anchor="n", font=tema.fonte(tema.TAM_CARDAPIO_FAIXA, forte=True),
                width=margem, justify="center", tags="texto",
            ), 14)

        if self._turma:
            tela.create_text(
                meio, y, text=self._turma, fill=tema.COR_SUCESSO_SUAVE,
                anchor="n", font=tema.fonte(tema.TAM_TURMA), tags="texto",
            )

        topo, base = tela.bbox("texto")[1], tela.bbox("texto")[3]
        tela.move("texto", 0, altura / 2 - (topo + base) / 2)

    def _desenhar_fundo_confirmacao(self, largura: int, altura: int) -> None:
        if (largura, altura) == self._tamanho_confirmacao:
            return
        self._tamanho_confirmacao = (largura, altura)

        imagem = formas.gradiente(
            largura, altura, tema.COR_SUCESSO, tema.COR_SUCESSO_ESCURA
        )
        if imagem is None:   # sem Pillow, o verde chapado de sempre
            return

        from PIL import ImageTk
        self._fundo_confirmacao = ImageTk.PhotoImage(imagem)
        self._painel_confirmacao.delete("degrade")
        self._painel_confirmacao.create_image(
            0, 0, image=self._fundo_confirmacao, anchor="nw", tags="degrade"
        )
        self._painel_confirmacao.tag_lower("degrade")

    # -----------------------------------------------------------------------
    # Cardápio
    # -----------------------------------------------------------------------
    def _buscar_cardapio(self) -> None:
        threading.Thread(target=self._consultar_cardapio, daemon=True).start()
        self._agendamento_cardapio = self.after(MILISSEGUNDOS_CARDAPIO, self._buscar_cardapio)

    def _consultar_cardapio(self) -> None:
        try:
            painel = self._cliente.painel_de_hoje()
        except ErroDeRede:
            # Sem servidor a tela continua inteira, só sem o cardápio. A fila
            # não para por causa disso.
            return
        cardapio = (painel.get("cardapio") or "").strip()
        if cardapio != self._cardapio:
            self._cardapio = cardapio
            self.after(0, self._aplicar_cardapio)

    def _aplicar_cardapio(self) -> None:
        self._desenhar_faixa()

    # -----------------------------------------------------------------------
    # Comportamento
    # -----------------------------------------------------------------------
    def _ao_digitar(self, _evento=None) -> None:
        encontrados = self._base.buscar(self._campo.get())
        self._lista.mostrar(encontrados)

        digitado = self._campo.get().strip()
        if digitado and len(digitado) >= 2 and not encontrados:
            self._dica.configure(
                text='Nenhum nome encontrado. Toque em "Não encontrei meu nome" abaixo.'
            )
            self._dica.pack(pady=tema.px(20))
        elif self._lista.truncada:
            # A lista não rola, então ela precisa dizer o que fazer para ver o
            # resto. Sem isto, quem tem sobrenome comum acha que não está lá.
            self._dica.configure(text="Digite mais letras para ver os outros nomes.")
            self._dica.pack(side="bottom", pady=tema.px(10))
        else:
            self._dica.pack_forget()

    def _escolher_primeiro(self, _evento=None) -> str:
        """Enter registra o primeiro da lista — atalho de quem já sabe usar."""
        primeiro = self._lista.primeiro
        if primeiro is not None:
            self._registrar(primeiro)
        return "break"

    def _registrar(self, aluno: dict) -> None:
        self.registrar_aluno(aluno, "nome")

    def registrar_aluno(self, aluno: dict, origem: str = "nome") -> None:
        """Registra o almoço e mostra a confirmação.

        `origem` distingue quem passou o cartão de quem digitou o nome. Além de
        virar estatística, é o que vai dizer à escola se valeu a pena imprimir
        os cartões — se quase todo mundo continuar digitando, o papel não pegou.
        """
        # Grava em disco e confirma na hora. Enviar ao servidor é problema da
        # thread de sincronização, não de quem está com o prato na mão.
        self._fila.registrar(aluno, origem)
        self._confirmar(aluno.get("nome", ""), "Bom almoço!", aluno.get("turma", ""))

    def _confirmar(self, nome: str, mensagem: str, turma: str = "") -> None:
        self._nome = nome
        self._mensagem_texto = mensagem
        self._turma = turma or ""
        self._pintar_confirmacao()

        # `Canvas.tkraise` não é o `tkraise` do Tk: no Canvas o nome significa
        # "levantar um item desenhado" e exige a tag do item. Para trazer o
        # painel inteiro à frente é preciso chamar o método original.
        tk.Misc.tkraise(self._painel_confirmacao)

        if self._retorno_agendado is not None:
            self.after_cancel(self._retorno_agendado)
        self._retorno_agendado = self.after(MILISSEGUNDOS_CONFIRMACAO, self.mostrar_busca)

    def mostrar_busca(self) -> None:
        self._retorno_agendado = None
        self._campo.delete(0, "end")
        self._lista.mostrar([])
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
    def definir_cartao_ativo(self, ativo: bool) -> None:
        """Mostra (ou esconde) o convite para usar o cartão.

        Só aparece quando a câmera abriu de verdade. Anunciar uma forma de
        identificação que não funciona seria pior que não anunciar nada: o
        aluno tentaria, não daria certo, e ele culparia o sistema.
        """
        if ativo == self._cartao_ativo:
            return
        self._cartao_ativo = ativo
        self._dica_cartao.configure(
            text="ou mostre seu cartão para a câmera" if ativo else ""
        )

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
