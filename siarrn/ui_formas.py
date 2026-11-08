"""
SIARRN — Primitivas de desenho

As formas que o Tkinter não tem. Este módulo existe porque o Tk só desenha
retângulos de canto reto: não há cantos arredondados, não há degradê, e o
`tk.Button` não aceita nenhum dos dois.

Tudo isto nasceu dentro da tela de início, como funções privadas. Enquanto
ficaram lá, nenhuma outra tela podia usá-las — e foi exatamente por isso que o
sistema acabou com duas aparências: a apresentação bonita e o resto chapado.

**Regra de degradação:** Pillow é opcional. Sem ele somem apenas os degradês,
que viram cor chapada. Cantos arredondados e botões continuam, porque são
Canvas puro. Nada aqui pode levantar exceção por falta de Pillow — o totem
fica sozinho no refeitório e ninguém está olhando um terminal.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from . import ui_tema as tema

try:
    from PIL import Image, ImageDraw, ImageTk
    PILLOW_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    PILLOW_DISPONIVEL = False


def rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Canvas puro — sempre disponível
# ---------------------------------------------------------------------------
def bloco_arredondado(tela, x1, y1, x2, y2, raio, cor, tags) -> "Bloco":
    """Retângulo de cantos arredondados no Canvas. Ver `Bloco`."""
    return Bloco(tela, x1, y1, x2, y2, raio, cor, tags)


# Desenhado neste tamanho e reduzido: é a redução que suaviza a borda.
SUPERAMOSTRAGEM = 4


def mascara_de_canto(raio: int):
    """Um disco de diâmetro 2·raio, com a borda suavizada. Precisa de Pillow."""
    grande = raio * 2 * SUPERAMOSTRAGEM
    mascara = Image.new("L", (grande, grande), 0)
    ImageDraw.Draw(mascara).ellipse([0, 0, grande - 1, grande - 1], fill=255)
    return mascara.resize((raio * 2, raio * 2), Image.LANCZOS)


def _cantos(tela, raio: int, cor: str) -> list:
    """Os quatro cantos de um raio e cor, criados uma vez por janela.

    O cache mora na janela raiz porque o PhotoImage pertence a ela: um cache
    global devolveria imagens de uma raiz já destruída.
    """
    cache = tela._root().__dict__.setdefault("_siarrn_cantos", {})
    chave = (raio, cor)
    if chave not in cache:
        disco = Image.new("RGBA", (raio * 2, raio * 2), (*rgb(cor), 255))
        disco.putalpha(mascara_de_canto(raio))
        cache[chave] = [
            ImageTk.PhotoImage(disco.crop(caixa), master=tela)
            for caixa in ((0, 0, raio, raio), (raio, 0, raio * 2, raio),
                          (0, raio, raio, raio * 2), (raio, raio, raio * 2, raio * 2))
        ]
    return cache[chave]


class Bloco:
    """Retângulo de cantos arredondados no Canvas.

    Dois retângulos cruzados formam a cruz central, e um canto em cada ponta
    completa a forma. Com Pillow, os cantos são imagens com a borda suavizada;
    sem ele, círculos do próprio Canvas. O Tk não suaviza nada no Windows, e
    os círculos saíam em degraus visíveis em todo botão e cartão do sistema.

    `mover` e `pintar` existem porque a lista de nomes reaproveita os mesmos
    blocos a cada tecla, em vez de apagar e recriar: recriar faz a lista piscar.
    """

    def __init__(self, tela, x1, y1, x2, y2, raio, cor, tags) -> None:
        self._tela = tela
        self._raio_pedido = raio
        self._raio = 0
        self._cor = cor
        self._suave = PILLOW_DISPONIVEL
        self._retas = [tela.create_rectangle(0, 0, 0, 0, fill=cor, outline="", tags=tags)
                       for _ in range(2)]
        if self._suave:
            self._cantos = [tela.create_image(0, 0, anchor="nw", tags=tags) for _ in range(4)]
        else:
            self._cantos = [tela.create_oval(0, 0, 0, 0, fill=cor, outline="", tags=tags)
                            for _ in range(4)]
        self.mover(x1, y1, x2, y2)

    def mover(self, x1, y1, x2, y2) -> None:
        # Coordenadas inteiras: em meio pixel os cantos e as retas deixariam
        # uma fresta entre eles.
        x1, y1, x2, y2 = (round(v) for v in (x1, y1, x2, y2))
        raio = int(max(0, min(self._raio_pedido, (x2 - x1) // 2, (y2 - y1) // 2)))
        self._raio = raio
        tela = self._tela
        tela.coords(self._retas[0], x1 + raio, y1, x2 - raio, y2)
        tela.coords(self._retas[1], x1, y1 + raio, x2, y2 - raio)

        cantos = ((x1, y1), (x2 - raio, y1), (x1, y2 - raio), (x2 - raio, y2 - raio))
        if self._suave:
            for item, ponto in zip(self._cantos, cantos):
                tela.coords(item, *ponto)
        else:
            diametro = raio * 2
            for item, (cx, cy) in zip(self._cantos, ((x1, y1), (x2 - diametro, y1),
                                                     (x1, y2 - diametro),
                                                     (x2 - diametro, y2 - diametro))):
                tela.coords(item, cx, cy, cx + diametro, cy + diametro)
        self.pintar(self._cor)

    def pintar(self, cor: str) -> None:
        self._cor = cor
        tela = self._tela
        for item in self._retas:
            tela.itemconfigure(item, fill=cor)
        if not self._suave:
            for item in self._cantos:
                tela.itemconfigure(item, fill=cor)
            return
        imagens = _cantos(tela, self._raio, cor) if self._raio > 0 else [""] * 4
        for item, imagem in zip(self._cantos, imagens):
            tela.itemconfigure(item, image=imagem)


# ---------------------------------------------------------------------------
# Degradês — dependem de Pillow
# ---------------------------------------------------------------------------
def gradiente(largura: int, altura: int, de: str, para: str, faixas: bool = False):
    """Degradê vertical, com faixas diagonais opcionais.

    Desenhado em vez de carregado de arquivo porque precisa se ajustar a
    qualquer resolução sem esticar nem cortar — a escola ainda não definiu que
    equipamento vai usar.

    Devolve `None` sem Pillow; quem chama cai para cor chapada.
    """
    if not PILLOW_DISPONIVEL or largura < 1 or altura < 1:
        return None

    cor_de, cor_para = rgb(de), rgb(para)
    imagem = Image.new("RGB", (largura, altura), cor_de)
    desenho = ImageDraw.Draw(imagem)

    # Linha a linha: são algumas centenas de operações em vez de milhões.
    for y in range(altura):
        proporcao = y / max(1, altura - 1)
        desenho.line(
            [(0, y), (largura, y)],
            fill=tuple(round(cor_de[i] + (cor_para[i] - cor_de[i]) * proporcao)
                       for i in range(3)),
        )

    if not faixas:
        return imagem

    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    pincel = ImageDraw.Draw(camada)
    passo = max(160, largura // 7)
    for indice in range(-2, largura // passo + 3):
        base = indice * passo
        pincel.polygon(
            [
                (base, altura),
                (base + passo * 0.5, altura),
                (base + passo * 0.5 + altura * 0.55, 0),
                (base + altura * 0.55, 0),
            ],
            fill=(46, 117, 182, 30),
        )

    return Image.alpha_composite(imagem.convert("RGBA"), camada).convert("RGB")


def arredondar_imagem(imagem, raio: int, borda: int = 0):
    """Arredonda os cantos de uma imagem e, opcionalmente, a contorna.

    A borda existe porque foto e fundo podem ficar parecidos demais — uma foto
    de parede azulada do refeitório sumiria dentro do azul da tela. O contorno
    âmbar garante que o painel se leia como um objeto sobre o fundo, em
    qualquer imagem que a escola coloque na pasta.
    """
    recortada = imagem.convert("RGBA")

    mascara = Image.new("L", imagem.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        [0, 0, imagem.width - 1, imagem.height - 1], radius=raio, fill=255
    )
    recortada.putalpha(mascara)

    if borda > 0:
        ImageDraw.Draw(recortada).rounded_rectangle(
            [borda // 2, borda // 2,
             imagem.width - 1 - borda // 2, imagem.height - 1 - borda // 2],
            radius=raio, outline=(*rgb(tema.COR_DESTAQUE), 235), width=borda,
        )
    return recortada


def campo(pai: tk.Misc, **kwargs) -> tk.Entry:
    """Campo de texto do sistema: borda clara do tema, azul quando em foco.

    A borda preta do `relief="solid"` era a única coisa de outra época nas
    telas, ao lado de botões e cartões arredondados.
    """
    opcoes = dict(
        relief="flat", borderwidth=0, highlightthickness=2,
        highlightbackground=tema.COR_BORDA, highlightcolor=tema.COR_SECUNDARIA,
        bg=tema.COR_CARD, fg=tema.COR_TEXTO, insertbackground=tema.COR_PRIMARIA,
    )
    opcoes.update(kwargs)
    return tk.Entry(pai, **opcoes)


class FaixaGradiente(tk.Canvas):
    """Uma faixa de cabeçalho em degradê.

    **Por que o conteúdo precisa ser desenhado, e não empacotado:** widgets do
    Tk não têm fundo transparente. Um `Label` azul posto sobre esta faixa
    cobriria o degradê com cor chapada, e a faixa inteira perderia a razão de
    existir. O texto, então, entra como item de Canvas — é o mesmo caminho que
    a tela de apresentação já segue.

    Widgets de verdade (um campo de digitação, um botão) entram por
    `create_window` e funcionam normalmente: eles têm cor própria e não
    deveriam mesmo deixar o fundo passar.

    Só vale a pena numa faixa alta. Num cabeçalho de noventa pixels o degradê
    é imperceptível, e lá o azul chapado continua sendo a escolha certa.

    Sem Pillow vira cor chapada e a única diferença é a textura.
    """

    def __init__(self, pai: tk.Misc, altura: int, de: str | None = None,
                 para: str | None = None, faixas: bool = False, **kwargs) -> None:
        self._de = de or tema.COR_PRIMARIA_ESCURA
        self._para = para or tema.COR_PRIMARIA
        self._faixas = faixas
        self._imagem = None
        self._tamanho = (0, 0)

        super().__init__(
            pai, bg=self._para, height=altura, highlightthickness=0, **kwargs
        )
        self.bind("<Configure>", self._ao_redimensionar)

    def _ao_redimensionar(self, evento) -> None:
        if (evento.width, evento.height) == self._tamanho:
            return
        self._tamanho = (evento.width, evento.height)
        self._repintar()

    def _repintar(self) -> None:
        largura, altura = self._tamanho
        imagem = gradiente(largura, altura, self._de, self._para, self._faixas)
        if imagem is None:
            return
        # A referência precisa ficar viva: o Tk não segura o PhotoImage.
        self._imagem = ImageTk.PhotoImage(imagem)
        self.delete("degrade")
        self.create_image(0, 0, image=self._imagem, anchor="nw", tags="degrade")
        self.tag_lower("degrade")


class CartaoArredondado(tk.Canvas):
    """Um painel de cantos arredondados que aceita widgets dentro.

    O conteúdo vai no `interior`, um Frame comum — de fora, usa-se este cartão
    como se usava o `tk.Frame` com `highlightthickness` de antes.

    **O truque, e por que ele funciona:** o Frame interno continua tendo cantos
    retos, e se ele ocupasse o cartão inteiro cobriria justamente o
    arredondamento. Por isso é embutido com uma folga de meio raio. Num raio de
    12, o canto do Frame fica em (6, 6), enquanto a borda arredondada nessa
    altura já passou por y≈1,6 — o canto reto cai dentro da forma e some.
    """

    def __init__(self, pai: tk.Misc, cor: str = tema.COR_CARD,
                 raio: int | None = None, fundo: str | None = None,
                 filete: str | None = None, **kwargs) -> None:
        self._cor = cor
        self._raio = tema.px(tema.RAIO_CANTO_PEQUENO) if raio is None else raio
        self._filete = filete
        self._tamanho = (0, 0)

        super().__init__(
            pai, bg=fundo or self._cor_do_pai(pai), highlightthickness=0, **kwargs
        )

        self.interior = tk.Frame(self, bg=cor)
        folga = self._raio // 2
        self._janela = self.create_window(folga, folga, window=self.interior, anchor="nw")
        self._folga = folga

        self.interior.bind("<Configure>", self._ao_mudar_conteudo)
        self.bind("<Configure>", self._ao_redimensionar)

    @staticmethod
    def _cor_do_pai(pai: tk.Misc) -> str:
        try:
            return pai.cget("bg")
        except tk.TclError:
            return tema.COR_FUNDO

    def _ao_mudar_conteudo(self, _evento) -> None:
        self.configure(height=self.interior.winfo_reqheight() + self._folga * 2)

    def _ao_redimensionar(self, evento) -> None:
        # Com menos altura do que o conteúdo pede, o interior é forçado a
        # caber: sem isso ele mantinha o tamanho natural e a borda do cartão
        # cortava a última linha. Com altura sobrando, volta ao natural (0).
        disponivel = evento.height - self._folga * 2
        apertado = disponivel < self.interior.winfo_reqheight()
        self.itemconfigure(self._janela, width=evento.width - self._folga * 2,
                           height=disponivel if apertado else 0)
        if (evento.width, evento.height) == self._tamanho:
            return
        self._tamanho = (evento.width, evento.height)
        self._desenhar()

    def _desenhar(self) -> None:
        largura, altura = self._tamanho
        self.delete("cartao")
        bloco_arredondado(self, 0, 0, largura, altura, self._raio, self._cor, "cartao")

        if self._filete:
            # O filete âmbar do SIGBEF, acompanhando o arredondamento do topo:
            # um retângulo reto escaparia pelos cantos.
            bloco_arredondado(
                self, 0, 0, largura, self._raio * 2, self._raio, self._filete, "cartao"
            )
            self.create_rectangle(
                0, tema.px(6), largura, self._raio * 2,
                fill=self._cor, outline="", tags="cartao",
            )

        self.tag_lower("cartao")


class BotaoArredondado(tk.Canvas):
    """Um botão com cantos arredondados.

    O `tk.Button` não arredonda canto nenhum: é a razão técnica de todos os
    botões do sistema terem sido retos até agora. Este é desenhado — retângulo
    arredondado mais texto, num Canvas do tamanho exato do conteúdo.

    A API imita a do `tk.Button` no que o projeto usa (`text`, `command`, `bg`,
    `fg`, `font`, `padx`, `pady`, `state`), para que a troca seja mecânica e o
    `configure(state=...)` de quem salva o cardápio continue funcionando.
    """

    def __init__(self, pai: tk.Misc, text: str, command=None,
                 bg: str = tema.COR_SECUNDARIA, fg: str = tema.COR_TEXTO_CLARO,
                 font=None, padx: int = 18, pady: int = 10,
                 raio: int | None = None, fundo: str | None = None) -> None:
        self._texto = text
        self._comando = command
        self._cor = bg
        self._cor_texto = fg
        self._fonte = font or tema.fonte(12, forte=True)
        self._raio = tema.px(tema.RAIO_CANTO_PEQUENO) if raio is None else raio
        self._desabilitado = False

        largura, altura = self._medir(pai, padx, pady)

        super().__init__(
            pai, width=largura, height=altura,
            bg=fundo or self._cor_do_pai(pai),
            highlightthickness=0, cursor="hand2",
        )
        self._largura, self._altura = largura, altura
        self._fundo: Bloco | None = None
        self._desenhar(self._cor)

        self.bind("<Button-1>", self._pressionar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Enter>", lambda e: self._pintar(tema.ajustar_cor(self._cor, 0.85)))
        self.bind("<Leave>", lambda e: self._pintar(self._cor))

    @staticmethod
    def _cor_do_pai(pai: tk.Misc) -> str:
        """O Canvas precisa do fundo de quem está atrás.

        Fora do retângulo arredondado o Canvas continua sendo um retângulo
        reto. Sem a cor do pai, o arredondamento aparece como quatro cantinhos
        de outra cor — o defeito clássico de botão desenhado.
        """
        try:
            return pai.cget("bg")
        except tk.TclError:
            return tema.COR_FUNDO

    def _medir(self, pai: tk.Misc, padx: int, pady: int) -> tuple[int, int]:
        try:
            medida = tkfont.Font(root=pai, font=self._fonte)
            largura_texto = medida.measure(self._texto)
            altura_texto = medida.metrics("linespace")
        except tk.TclError:  # pragma: no cover - só sem display
            largura_texto, altura_texto = len(self._texto) * 9, 18
        return largura_texto + padx * 2, altura_texto + pady * 2

    def _desenhar(self, cor: str) -> None:
        self.delete("all")
        self._fundo = bloco_arredondado(
            self, 1, 1, self._largura - 1, self._altura - 1, self._raio, cor, "fundo"
        )
        self.create_text(
            self._largura / 2, self._altura / 2, text=self._texto,
            fill=self._cor_texto, font=self._fonte, tags="rotulo",
        )

    def _pintar(self, cor: str) -> None:
        if self._desabilitado:
            return
        self._fundo.pintar(cor)

    def _pressionar(self, _evento=None) -> None:
        self._pintar(tema.ajustar_cor(self._cor, 0.70))

    def _soltar(self, _evento=None) -> None:
        if self._desabilitado:
            return
        self._pintar(tema.ajustar_cor(self._cor, 0.85))
        if self._comando is not None:
            self._comando()

    # -----------------------------------------------------------------------
    # Compatibilidade com tk.Button
    # -----------------------------------------------------------------------
    def configure(self, **kwargs):  # type: ignore[override]
        estado = kwargs.pop("state", None)
        texto = kwargs.pop("text", None)

        if texto is not None:
            self._texto = texto
            self.itemconfigure("rotulo", text=texto)

        if estado is not None:
            self._desabilitado = estado == "disabled"
            # Repintar direto: `_pintar` respeita o estado e não serviria aqui.
            cor = tema.mesclar_branco(self._cor, 0.55) if self._desabilitado else self._cor
            self._fundo.pintar(cor)
            super().configure(cursor="" if self._desabilitado else "hand2")

        if kwargs:
            super().configure(**kwargs)
        return None

    config = configure
