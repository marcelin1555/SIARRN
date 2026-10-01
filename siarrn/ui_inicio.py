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

from . import config_totem, log, ui_formas as formas, ui_tema as tema
from .cliente_api import ErroDeRede

try:
    from PIL import Image, ImageTk
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

        O desenho em si vive em `ui_formas`, porque as outras telas usam o
        mesmo degradê no cabeçalho. Aqui ficam só as escolhas desta tela: as
        faixas diagonais, que são da apresentação e de mais nenhuma.
        """
        return formas.gradiente(
            largura, altura, tema.COR_PRIMARIA_ESCURA, tema.COR_PRIMARIA, faixas=True
        )

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

        tingimento = Image.new("RGB", imagem.size, formas.rgb(tema.COR_PRIMARIA))
        imagem = Image.blend(imagem, tingimento, FORCA_DO_TINGIMENTO)

        return formas.arredondar_imagem(imagem, tema.px(tema.RAIO_CANTO), borda=tema.px(3))

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
            formas.bloco_arredondado(
                self._tela, x_foto, y_foto, x_foto + largura_foto, y_foto + altura_foto,
                tema.px(tema.RAIO_CANTO), tema.COR_SECUNDARIA, "conteudo",
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

        formas.bloco_arredondado(
            self._tela, x - metade, y - meia_altura, x + metade, y + meia_altura,
            tema.px(tema.RAIO_CANTO), tema.COR_SUCESSO, "conteudo",
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
