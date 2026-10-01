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
def bloco_arredondado(tela, x1, y1, x2, y2, raio, cor, tags):
    """Retângulo de cantos arredondados no Canvas.

    Composto de dois retângulos cruzados mais um círculo em cada canto — o
    resultado tem cantos exatos, ao contrário do `create_polygon` com `smooth`,
    que aproxima por spline e deforma quando o raio é grande em relação ao lado.

    Devolve os ids criados, para quem precisar trocar a cor depois sem
    redesenhar — é o que o hover da lista de nomes faz a cada movimento do dedo.
    """
    raio = max(0, min(raio, (x2 - x1) / 2, (y2 - y1) / 2))
    diametro = raio * 2

    ids = [
        tela.create_rectangle(x1 + raio, y1, x2 - raio, y2, fill=cor, outline="", tags=tags),
        tela.create_rectangle(x1, y1 + raio, x2, y2 - raio, fill=cor, outline="", tags=tags),
    ]
    for cx, cy in ((x1, y1), (x2 - diametro, y1),
                   (x1, y2 - diametro), (x2 - diametro, y2 - diametro)):
        ids.append(
            tela.create_oval(cx, cy, cx + diametro, cy + diametro,
                             fill=cor, outline="", tags=tags)
        )
    return ids


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

    def _ao_mudar_conteudo(self, evento) -> None:
        self.configure(height=evento.height + self._folga * 2)

    def _ao_redimensionar(self, evento) -> None:
        self.itemconfigure(self._janela, width=evento.width - self._folga * 2)
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
        self._ids_fundo: list[int] = []
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
        self._ids_fundo = bloco_arredondado(
            self, 1, 1, self._largura - 1, self._altura - 1, self._raio, cor, "fundo"
        )
        self.create_text(
            self._largura / 2, self._altura / 2, text=self._texto,
            fill=self._cor_texto, font=self._fonte, tags="rotulo",
        )

    def _pintar(self, cor: str) -> None:
        if self._desabilitado:
            return
        for item in self._ids_fundo:
            self.itemconfigure(item, fill=cor)

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
            for item in self._ids_fundo:
                self.itemconfigure(item, fill=cor)
            super().configure(cursor="" if self._desabilitado else "hand2")

        if kwargs:
            super().configure(**kwargs)
        return None

    config = configure
