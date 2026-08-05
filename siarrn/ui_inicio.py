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

from . import ui_tema as tema
from .cliente_api import ErroDeRede

try:
    from PIL import Image, ImageTk
    PILLOW_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    PILLOW_DISPONIVEL = False

PASTA_FOTOS = Path(__file__).resolve().parent.parent / "assets" / "fotos"
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

# Quanto o fundo é puxado para o azul institucional. Escurece o suficiente para
# o texto branco ficar legível sobre qualquer foto, e de quebra faz fotos de
# origens diferentes parecerem da mesma família.
FORCA_DO_TINGIMENTO = 0.55


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
        self._largura = 0
        self._altura = 0

        self._tela = tk.Canvas(
            self, bg=tema.COR_PRIMARIA, highlightthickness=0, cursor="hand2"
        )
        self._tela.pack(fill="both", expand=True)

        self._tela.bind("<Configure>", self._ao_redimensionar)
        for evento in ("<Button-1>", "<Key>"):
            self._tela.bind(evento, self._entrar)
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
        self._desenhar_conteudo()

        if PILLOW_DISPONIVEL and self._largura > 1 and self._altura > 1:
            threading.Thread(target=self._carregar_fotos, daemon=True).start()

    def _carregar_fotos(self) -> None:
        """Abre, recorta e tinge as fotos — fora da thread da interface.

        Redimensionar meia dúzia de imagens grandes leva alguns segundos numa
        máquina modesta, e a tela precisa aparecer antes disso.
        """
        largura, altura = self._largura, self._altura
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
                print(f"Ignorando {caminho.name}: {erro}")

        if not preparadas or (largura, altura) != (self._largura, self._altura):
            return

        self._fotos = preparadas
        self.after(0, self._comecar_rotacao)

    @staticmethod
    def _ajustar(original, largura: int, altura: int):
        """Recorta a foto para preencher a tela e a puxa para o azul da escola."""
        imagem = original.convert("RGB")

        proporcao = max(largura / imagem.width, altura / imagem.height)
        novo = (max(1, round(imagem.width * proporcao)), max(1, round(imagem.height * proporcao)))
        imagem = imagem.resize(novo, Image.LANCZOS)

        esquerda = (imagem.width - largura) // 2
        topo = (imagem.height - altura) // 2
        imagem = imagem.crop((esquerda, topo, esquerda + largura, topo + altura))

        tingimento = Image.new("RGB", imagem.size, _rgb(tema.COR_PRIMARIA))
        return Image.blend(imagem, tingimento, FORCA_DO_TINGIMENTO)

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
        self._tela.delete("fundo")
        self._tela.create_image(0, 0, image=self._quadro_atual, anchor="nw", tags="fundo")
        self._tela.tag_lower("fundo")
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
        """Desenha o bloco central, centrado verticalmente.

        A altura é somada antes de desenhar qualquer coisa, e o bloco inteiro é
        centralizado a partir dela. Ancorar cada peça numa fração fixa da tela
        parece funcionar até o conteúdo mudar de tamanho — sem cardápio, ou com
        um cardápio que quebra em duas linhas, a composição abre um buraco no
        meio. Somando primeiro, o espaçamento se mantém em qualquer caso.
        """
        self._tela.delete("conteudo")

        largura = self._largura or self._tela.winfo_width()
        altura = self._altura or self._tela.winfo_height()
        if largura <= 1 or altura <= 1:
            return

        meio = largura // 2
        largura_texto = largura - tema.px(220)
        tem_cardapio = bool(self._cardapio)

        # Duas linhas de cardápio cabem no espaço de uma e meia; acima disso a
        # fonte é grande o bastante para o texto ocupar o dobro.
        linhas_cardapio = 2 if tem_cardapio and len(self._cardapio) > 42 else 1

        alturas = [
            tema.px(78),                                     # nome
            tema.px(34),                                     # subtítulo
            tema.px(30),                                     # régua âmbar
        ]
        if tem_cardapio:
            alturas += [tema.px(46), tema.px(40) * linhas_cardapio]
        alturas += [tema.px(58), tema.px(74)]                 # respiro + botão

        y = (altura - sum(alturas)) / 2 + tema.px(30)

        self._tela.create_text(
            meio, y, text="SIARRN", fill=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_INICIO_NOME, forte=True), tags="conteudo",
        )
        y += tema.px(62)

        self._tela.create_text(
            meio, y, text="Sistema Integrado de Almoço e Refeição",
            fill=tema.COR_PRIMARIA_SUAVE,
            font=tema.fonte(tema.TAM_INICIO_SUB), tags="conteudo",
        )
        y += tema.px(26)

        self._tela.create_rectangle(
            meio - tema.px(60), y, meio + tema.px(60), y + tema.px(5),
            fill=tema.COR_DESTAQUE, outline="", tags="conteudo",
        )
        y += tema.px(50)

        if tem_cardapio:
            self._tela.create_text(
                meio, y, text="HOJE NO ALMOÇO", fill=tema.COR_DESTAQUE,
                font=tema.fonte(tema.TAM_INICIO_CARDAPIO_ROTULO, forte=True), tags="conteudo",
            )
            y += tema.px(40)
            self._tela.create_text(
                meio, y, text=self._cardapio, fill=tema.COR_TEXTO_CLARO,
                font=tema.fonte(tema.TAM_INICIO_CARDAPIO), width=largura_texto,
                justify="center", tags="conteudo",
            )
            y += tema.px(34) * linhas_cardapio

        y += tema.px(56)
        self._desenhar_chamada(meio, y, largura)
        self._desenhar_pontos(meio, altura - tema.px(44))

    def _desenhar_chamada(self, meio: int, y: float, largura: int) -> None:
        """O convite para tocar.

        Desenhado como retângulo no próprio Canvas, e não como botão de verdade,
        porque o alvo real é a tela inteira — numa fila, ninguém deveria precisar
        acertar um retângulo. Ele existe para dizer o que fazer, não para ser o
        único lugar clicável.
        """
        metade = min(largura // 2 - tema.px(40), tema.px(290))
        meia_altura = tema.px(33)

        self._tela.create_rectangle(
            meio - metade, y - meia_altura, meio + metade, y + meia_altura,
            fill=tema.COR_SUCESSO, outline="", tags="conteudo",
        )
        self._tela.create_text(
            meio, y, text="Toque para registrar seu almoço", fill=tema.COR_TEXTO_CLARO,
            font=tema.fonte(tema.TAM_INICIO_CHAMADA, forte=True), tags="conteudo",
        )

    def _desenhar_pontos(self, meio: int, y: float) -> None:
        """Indicador de quantas fotos existem e em qual delas estamos."""
        if len(self._fotos) < 2:
            return

        raio = tema.px(5)
        espaco = tema.px(20)
        inicio = meio - (len(self._fotos) - 1) * espaco / 2

        for indice in range(len(self._fotos)):
            x = inicio + indice * espaco
            atual = indice == self._indice
            self._tela.create_oval(
                x - raio, y - raio, x + raio, y + raio,
                fill=tema.COR_DESTAQUE if atual else tema.COR_PRIMARIA_SUAVE,
                outline="", tags="conteudo",
            )


def _rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
