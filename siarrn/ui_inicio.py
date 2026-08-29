"""
SIARRN — A tela de início do totem

É o que fica na tela quando ninguém está usando: o nome do sistema, fotos do
refeitório passando devagar, e o cardápio do dia. Serve a três propósitos ao
mesmo tempo, e todos eles importam:

* **É o que a escola vê de longe.** O totem passa a maior parte do dia parado.
  Uma tela viva e com a identidade da escola é o que faz a coordenação olhar
  para o equipamento e enxergar um sistema, não um computador esquecido ligado.
* **Responde a pergunta do aluno antes de ele perguntar.** O cardápio aparece
  aqui em letras grandes, então dá para saber o que tem no almoço de longe, sem
  encostar em nada.
* **Protege a tela.** Conteúdo estático por horas marca painéis mais baratos.

Toque em qualquer lugar leva à busca. A tela inteira é o botão — numa fila, o
alvo não pode ser um retângulo pequeno no meio.

Pillow é opcional: sem ele, ou sem fotos na pasta, o fundo passa a ser o azul
institucional sólido e todo o resto continua igual.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from pathlib import Path

from . import config_totem, log, ui_tema as tema
from .cliente_api import ErroDeRede

try:
    from PIL import Image, ImageDraw, ImageTk
    PILLOW_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    PILLOW_DISPONIVEL = False

PASTA_FOTOS = config_totem.pasta_do_programa() / "assets" / "fotos"
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")

# Quanto tempo cada foto fica parada antes da próxima.
MILISSEGUNDOS_POR_FOTO = 7000

# A transição inteira, dividida em passos.
MILISSEGUNDOS_TRANSICAO = 520
PASSOS_TRANSICAO = 13

# Acima disto por quadro, a máquina não dá conta do crossfade e ele é desligado.
# A escola ainda não definiu o equipamento, e pode muito bem ser um PC velho:
# melhor troca seca do que uma animação travando na frente de todo mundo.
LIMITE_MS_POR_QUADRO = 45

MILISSEGUNDOS_CARDAPIO = 60_000

# Quanto a foto é puxada para o azul institucional.
#
# É pouco de propósito. A foto ocupa um painel só dela, sem texto por cima, e
# portanto não precisa ser escurecida para nada ficar legível — o tingimento
# aqui serve apenas para que fotos tiradas em dias, luzes e câmeras diferentes
# pareçam da mesma família.
FORCA_DO_TINGIMENTO = 0.18

# Quanto da largura o painel da foto ocupa.
FATIA_DA_FOTO = 0.40

# Arredondamento dos cantos do painel da foto e do botão.
RAIO_CANTO = 26


class TelaInicio(tk.Frame):
    def __init__(self, master, cliente, ao_entrar) -> None:
        super().__init__(master, bg=tema.COR_PRIMARIA)
        self._cliente = cliente
        self._ao_entrar = ao_entrar

        self._fotos: list = []          # PIL.Image já ajustadas à tela
        self._quadro_atual = None       # ImageTk.PhotoImage em exibição
        self._indice = 0
        self._agendamento = None
        self._agendamento_cardapio = None
        self._crossfade_ligado = True
        self._cardapio = ""
        self._cartao_ativo = False
        self._largura = 0
        self._altura = 0

        self._area_foto = (0, 0, 0, 0)   # x, y, largura, altura do painel da foto
        self._fundo = None               # ImageTk do fundo institucional

        self._tela = tk.Canvas(
            self, bg=tema.COR_PRIMARIA, highlightthickness=0, cursor="hand2"
        )
        self._tela.pack(fill="both", expand=True)

        self._tela.bind("<Configure>", self._ao_redimensionar)
        # Só o toque entra. Teclas não: num refeitório o teclado fica exposto, e
        # qualquer encostão pularia a apresentação — inclusive eventos residuais
        # de quem acabou de iniciar o programa pelo terminal.
        self._tela.bind("<Button-1>", self._entrar)
        self.bind("<Button-1>", self._entrar)

    # -----------------------------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------------------------
    def iniciar(self) -> None:
        self._buscar_cardapio()
        self._agendar_cardapio()
        self._tela.focus_set()

    def parar(self) -> None:
        for agendamento in (self._agendamento, self._agendamento_cardapio):
            if agendamento is not None:
                self.after_cancel(agendamento)
        self._agendamento = None
        self._agendamento_cardapio = None

    def _entrar(self, _evento=None) -> None:
        self.parar()
        self._ao_entrar()

    # -----------------------------------------------------------------------
    # Fotos
    # -----------------------------------------------------------------------
    def _ao_redimensionar(self, evento) -> None:
        # O Tk dispara <Configure> várias vezes durante a montagem; só vale
        # recarregar as fotos quando o tamanho realmente mudou.
        if (evento.width, evento.height) == (self._largura, self._altura):
            self._desenhar_conteudo()
            return

        self._largura, self._altura = evento.width, evento.height
        self._calcular_area_foto()
        self._desenhar_conteudo()

        if PILLOW_DISPONIVEL and self._largura > 1 and self._altura > 1:
            threading.Thread(target=self._carregar_fotos, daemon=True).start()

    def _calcular_area_foto(self) -> None:
        """O painel da foto: uma faixa vertical à esquerda, com margem."""
        margem = tema.px(26)
        largura = round(self._largura * FATIA_DA_FOTO)
        altura = self._altura - margem * 2
        self._area_foto = (margem, margem, max(1, largura), max(1, altura))

    def _carregar_fotos(self) -> None:
        """Monta o fundo institucional e prepara as fotos — fora da interface.

        Gerar o fundo e redimensionar meia dúzia de imagens grandes leva alguns
        segundos numa máquina modesta, e a tela precisa aparecer antes disso.
        """
        largura_tela, altura_tela = self._largura, self._altura
        fundo = self._gerar_fundo(largura_tela, altura_tela)
        if (largura_tela, altura_tela) == (self._largura, self._altura):
            self.after(0, lambda: self._aplicar_fundo(fundo))

        _, _, largura, altura = self._area_foto
        arquivos = sorted(
            caminho for caminho in PASTA_FOTOS.glob("*")
            if caminho.suffix.lower() in EXTENSOES
        )

        preparadas = []
        for caminho in arquivos:
            try:
                with Image.open(caminho) as original:
                    preparadas.append(self._ajustar(original, largura, altura))
            except Exception as erro:  # noqa: BLE001
                # Uma foto ruim na pasta não pode impedir o totem de abrir.
                log.aviso(f"Ignorando {caminho.name}: {erro}")

        if not preparadas or (largura, altura) != self._area_foto[2:]:
            return

        self._fotos = preparadas
        self.after(0, self._comecar_rotacao)

    @staticmethod
    def _gerar_fundo(largura: int, altura: int):
        """O fundo da tela: degradê azul com faixas diagonais largas.

        Desenhado aqui em vez de carregado de um arquivo porque precisa se
        ajustar a qualquer resolução sem esticar nem cortar — a escola ainda não
        definiu o equipamento. É a mesma linguagem das faixas sólidas do SIGBEF.
        """
        de, para = _rgb("#12314F"), _rgb(tema.COR_PRIMARIA)
        imagem = Image.new("RGB", (largura, altura), de)
        desenho = ImageDraw.Draw(imagem)

        # Linha a linha: são algumas centenas de operações em vez de milhões.
        for y in range(altura):
            proporcao = y / max(1, altura)
            desenho.line(
                [(0, y), (largura, y)],
                fill=tuple(round(de[i] + (para[i] - de[i]) * proporcao) for i in range(3)),
            )

        faixas = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
        pincel = ImageDraw.Draw(faixas)
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

        return Image.alpha_composite(imagem.convert("RGBA"), faixas).convert("RGB")

    def _aplicar_fundo(self, imagem) -> None:
        self._fundo = ImageTk.PhotoImage(imagem)
        self._tela.delete("papel")
        self._tela.create_image(0, 0, image=self._fundo, anchor="nw", tags="papel")
        self._ordenar_camadas()
        self._desenhar_conteudo()

    def _ordenar_camadas(self) -> None:
        """Empilha o desenho: papel embaixo, foto no meio, texto por cima.

        A ordem precisa ser imposta toda vez que uma camada é recriada. Cada
        `tag_lower` manda o item para o fim da pilha, então dois deles em
        sequência invertem a ordem entre si — foi assim que a foto acabou
        escondida atrás do fundo.
        """
        self._tela.tag_lower("fundo")
        self._tela.tag_lower("papel")

    @staticmethod
    def _ajustar(original, largura: int, altura: int):
        """Recorta a foto para o painel e arredonda os cantos."""
        imagem = original.convert("RGB")

        proporcao = max(largura / imagem.width, altura / imagem.height)
        novo = (max(1, round(imagem.width * proporcao)), max(1, round(imagem.height * proporcao)))
        imagem = imagem.resize(novo, Image.LANCZOS)

        esquerda = (imagem.width - largura) // 2
        topo = (imagem.height - altura) // 2
        imagem = imagem.crop((esquerda, topo, esquerda + largura, topo + altura))

        tingimento = Image.new("RGB", imagem.size, _rgb(tema.COR_PRIMARIA))
        imagem = Image.blend(imagem, tingimento, FORCA_DO_TINGIMENTO)

        return _arredondar(imagem, tema.px(RAIO_CANTO), borda=tema.px(3))

    def _comecar_rotacao(self) -> None:
        if not self._fotos:
            return
        self._indice = 0
        self._exibir(self._fotos[0])
        self._agendar_proxima()

    def _agendar_proxima(self) -> None:
        if self._agendamento is not None:
            self.after_cancel(self._agendamento)
        if len(self._fotos) > 1:
            self._agendamento = self.after(MILISSEGUNDOS_POR_FOTO, self._proxima)

    def _proxima(self) -> None:
        anterior = self._fotos[self._indice]
        self._indice = (self._indice + 1) % len(self._fotos)
        seguinte = self._fotos[self._indice]

        if self._crossfade_ligado:
            self._transicionar(anterior, seguinte, passo=1)
        else:
            self._exibir(seguinte)
            self._agendar_proxima()

    def _transicionar(self, de, para, passo: int) -> None:
        if passo > PASSOS_TRANSICAO:
            self._exibir(para)
            self._agendar_proxima()
            return

        inicio = time.perf_counter()
        self._exibir(Image.blend(de, para, passo / PASSOS_TRANSICAO))
        gasto = (time.perf_counter() - inicio) * 1000

        if gasto > LIMITE_MS_POR_QUADRO:
            # Máquina não dá conta: conclui esta troca de uma vez e não tenta
            # animar de novo. Vale para o resto da sessão.
            self._crossfade_ligado = False
            self._exibir(para)
            self._agendar_proxima()
            return

        self.after(
            max(1, MILISSEGUNDOS_TRANSICAO // PASSOS_TRANSICAO),
            lambda: self._transicionar(de, para, passo + 1),
        )

    def _exibir(self, imagem) -> None:
        # A referência precisa ficar viva: o Tk não segura o PhotoImage, e sem
        # isto a imagem some assim que o coletor de lixo passa.
        self._quadro_atual = ImageTk.PhotoImage(imagem)
        x, y, _, _ = self._area_foto
        self._tela.delete("fundo")
        self._tela.create_image(x, y, image=self._quadro_atual, anchor="nw", tags="fundo")
        self._ordenar_camadas()
        self._desenhar_conteudo()

    # -----------------------------------------------------------------------
    # Cardápio
    # -----------------------------------------------------------------------
    def _agendar_cardapio(self) -> None:
        self._agendamento_cardapio = self.after(MILISSEGUNDOS_CARDAPIO, self._ciclo_cardapio)

    def _ciclo_cardapio(self) -> None:
        self._buscar_cardapio()
        self._agendar_cardapio()

    def _buscar_cardapio(self) -> None:
        threading.Thread(target=self._consultar_cardapio, daemon=True).start()

    def _consultar_cardapio(self) -> None:
        try:
            painel = self._cliente.painel_de_hoje()
        except ErroDeRede:
            # Sem servidor a tela continua bonita, só sem o cardápio. Não é
            # motivo para mostrar erro a quem está passando pelo refeitório.
            return
        cardapio = (painel.get("cardapio") or "").strip()
        if cardapio != self._cardapio:
            self._cardapio = cardapio
            self.after(0, self._desenhar_conteudo)

    # -----------------------------------------------------------------------
    # Conteúdo por cima do fundo
    # -----------------------------------------------------------------------
    def _desenhar_conteudo(self) -> None:
        """Duas colunas: a foto de um lado, o que se lê do outro.

        A foto num painel próprio, em vez de fundo da tela inteira, muda mais
        do que a aparência. Ela deixa de ser pano de fundo atrás do texto e
        passa a ser conteúdo — dá para mostrar o refeitório de verdade sem
        precisar escurecer a imagem até sobrar só uma mancha azul.
        """
        self._tela.delete("conteudo")

        largura = self._largura or self._tela.winfo_width()
        altura = self._altura or self._tela.winfo_height()
        if largura <= 1 or altura <= 1:
            return

        x_foto, y_foto, largura_foto, altura_foto = self._area_foto

        # Sem Pillow ou sem fotos na pasta, o painel vira um bloco sólido mais
        # claro que o fundo — o suficiente para a composição continuar de pé.
        if not self._fotos:
            _bloco_arredondado(
                self._tela, x_foto, y_foto, x_foto + largura_foto, y_foto + altura_foto,
                tema.px(RAIO_CANTO), tema.COR_SECUNDARIA, "conteudo",
            )

        self._desenhar_pontos(x_foto + largura_foto / 2, y_foto + altura_foto - tema.px(26))
        self._desenhar_coluna_de_texto(x_foto + largura_foto, largura, altura)

    def _desenhar_coluna_de_texto(self, fim_da_foto: int, largura: int, altura: int) -> None:
        inicio = fim_da_foto + tema.px(40)
        largura_util = largura - inicio - tema.px(40)
        meio = inicio + largura_util / 2

        tem_cardapio = bool(self._cardapio)
        linhas_cardapio = 2 if tem_cardapio and len(self._cardapio) > 34 else 1

        # O bloco de texto é centralizado na metade de cima; o botão fica na de
        # baixo. Somar as alturas antes de desenhar mantém o espaçamento certo
        # quando o cardápio some ou quebra em duas linhas.
        alturas = [tema.px(74), tema.px(32), tema.px(28)]
        if tem_cardapio:
            alturas += [tema.px(44), tema.px(38) * linhas_cardapio]

        y = altura * 0.30 - sum(alturas) / 2

        self._tela.create_text(
            meio, y, text="SIARRN", fill=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_INICIO_NOME, forte=True), tags="conteudo",
        )
        y += tema.px(60)

        self._tela.create_text(
            meio, y, text="Sistema Integrado de Almoço e Refeição",
            fill=tema.COR_PRIMARIA_SUAVE, width=largura_util, justify="center",
            font=tema.fonte(tema.TAM_INICIO_SUB), tags="conteudo",
        )
        y += tema.px(26)

        self._tela.create_rectangle(
            meio - tema.px(58), y, meio + tema.px(58), y + tema.px(5),
            fill=tema.COR_DESTAQUE, outline="", tags="conteudo",
        )
        y += tema.px(48)

        if tem_cardapio:
            # Sobre o fundo escuro o âmbar volta a ter contraste de leitura, e
            # pode carregar o rótulo em vez de ficar só na régua.
            self._tela.create_text(
                meio, y, text="HOJE NO ALMOÇO", fill=tema.COR_DESTAQUE,
                font=tema.fonte(tema.TAM_INICIO_CARDAPIO_ROTULO, forte=True), tags="conteudo",
            )
            y += tema.px(38)
            self._tela.create_text(
                meio, y, text=self._cardapio, fill=tema.COR_TEXTO_CLARO,
                font=tema.fonte(tema.TAM_INICIO_CARDAPIO), width=largura_util,
                justify="center", tags="conteudo",
            )

        self._desenhar_botao(meio, altura * 0.74, largura_util)

        if self._cartao_ativo:
            self._tela.create_text(
                meio, altura * 0.74 + tema.px(72),
                text="ou mostre seu cartão para a câmera",
                fill=tema.COR_PRIMARIA_SUAVE,
                font=tema.fonte(tema.TAM_INICIO_SUB), tags="conteudo",
            )

    def definir_cartao_ativo(self, ativo: bool) -> None:
        """Anuncia o cartão só quando a câmera abriu de verdade."""
        if ativo != self._cartao_ativo:
            self._cartao_ativo = ativo
            self._desenhar_conteudo()

    def _desenhar_botao(self, x: float, y: float, largura_util: float) -> None:
        """O botão, como retângulo de cantos arredondados.

        Ele diz o que fazer, mas não é o único lugar clicável: a tela inteira
        responde ao toque. Numa fila de cem adolescentes, ninguém deveria
        precisar acertar um alvo.
        """
        metade = min(largura_util * 0.42, tema.px(250))
        meia_altura = tema.px(46)

        _bloco_arredondado(
            self._tela, x - metade, y - meia_altura, x + metade, y + meia_altura,
            tema.px(RAIO_CANTO), tema.COR_SUCESSO, "conteudo",
        )
        self._tela.create_text(
            x, y, text="TOQUE PARA COMEÇAR", fill=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_INICIO_CHAMADA, forte=True),
            justify="center", tags="conteudo",
        )

    def _desenhar_pontos(self, x: float, y: float) -> None:
        """Quantas fotos existem e em qual delas estamos, na base do painel."""
        if len(self._fotos) < 2:
            return

        raio = tema.px(5)
        espaco = tema.px(20)
        inicio = x - (len(self._fotos) - 1) * espaco / 2

        for indice in range(len(self._fotos)):
            centro = inicio + indice * espaco
            atual = indice == self._indice
            self._tela.create_oval(
                centro - raio, y - raio, centro + raio, y + raio,
                fill=tema.COR_DESTAQUE if atual else tema.COR_TEXTO_CLARO,
                outline="", tags="conteudo",
            )


def _rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))


def _arredondar(imagem, raio: int, borda: int = 0):
    """Arredonda os cantos e contorna o painel.

    A borda existe porque foto e fundo podem ficar parecidos demais — uma foto
    de parede azulada do refeitório sumiria dentro do azul da tela. O contorno
    âmbar garante que o painel se leia como um objeto sobre o fundo, em qualquer
    imagem que a escola coloque na pasta.
    """
    recortada = imagem.convert("RGBA")

    mascara = Image.new("L", imagem.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        [0, 0, imagem.width - 1, imagem.height - 1], radius=raio, fill=255
    )
    recortada.putalpha(mascara)

    if borda > 0:
        ImageDraw.Draw(recortada).rounded_rectangle(
            [borda // 2, borda // 2, imagem.width - 1 - borda // 2, imagem.height - 1 - borda // 2],
            radius=raio, outline=(*_rgb(tema.COR_DESTAQUE), 235), width=borda,
        )
    return recortada


def _bloco_arredondado(tela, x1, y1, x2, y2, raio, cor, tags) -> None:
    """Retângulo de cantos arredondados no Canvas.

    O Tk não tem essa primitiva. Composto de dois retângulos cruzados mais um
    círculo em cada canto — o resultado tem cantos exatos, ao contrário do
    `create_polygon` com `smooth`, que aproxima por spline e deforma quando o
    raio é grande em relação ao lado.
    """
    diametro = raio * 2
    tela.create_rectangle(x1 + raio, y1, x2 - raio, y2, fill=cor, outline="", tags=tags)
    tela.create_rectangle(x1, y1 + raio, x2, y2 - raio, fill=cor, outline="", tags=tags)
    for cx, cy in ((x1, y1), (x2 - diametro, y1), (x1, y2 - diametro), (x2 - diametro, y2 - diametro)):
        tela.create_oval(cx, cy, cx + diametro, cy + diametro, fill=cor, outline="", tags=tags)
