"""
SIARRN — Tema visual

A paleta é a mesma do SIGBEF, com os valores copiados de `sigbef/ui_tema.py`
sem aproximação. Os dois sistemas são apresentados juntos na escola e precisam
parecer da mesma família; se um dia a paleta do SIGBEF mudar, é aqui que se
mexe.

O vocabulário de cor também é herdado, com os mesmos significados do terminal
de autoatendimento da biblioteca: **verde é ação positiva, laranja é atenção,
azul é informação**. Quem já usa o SIGBEF lê o SIARRN sem aprender nada novo.

**A forma, porém, é própria do SIARRN.** O SIGBEF usa blocos de cor chapada e
cantos retos, e isso serve a ele: é lido sentado, a meio metro, por quem já
sabe o que veio fazer. O totem não. Ele fica horas parado onde a escola inteira
passa, é lido de pé a três metros, e precisa convidar alguém de bandeja na mão
a encostar nele. Por isso aqui existem cantos arredondados e degradês — a
mesma paleta e o mesmo vocabulário de cor, em formas que funcionam de longe.

Os degradês dependem de Pillow e caem para cor chapada sem ele; os cantos
arredondados são Canvas puro e nunca somem. As duas coisas vivem em
`ui_formas.py`.

O que este tema tem e o do SIGBEF não precisa: **escala por tamanho de tela**.
O SIGBEF é lido sentado, a meio metro do monitor. O totem é lido de pé, a três
metros, por alguém de bandeja na mão — e a escola ainda não definiu que
equipamento vai usar. As fontes se ajustam à altura da tela para que a mesma
interface funcione num monitor velho de 768px e num de 1080p.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Paleta — valores idênticos aos de sigbef/ui_tema.py
# ---------------------------------------------------------------------------
COR_PRIMARIA = "#1F4E79"      # faixa de cabeçalho, números de destaque
COR_SECUNDARIA = "#2E75B6"    # informação
COR_DESTAQUE = "#F2A900"      # âmbar, em doses pequenas
COR_FUNDO = "#F5F7FA"
COR_SUCESSO = "#2E7D32"       # ação positiva — a tela de confirmação
COR_ERRO = "#C62828"
COR_AVISO = "#EF6C00"         # atenção
COR_TEXTO = "#1A1A1A"
COR_TEXTO_CLARO = "#FFFFFF"
COR_CARD = "#FFFFFF"
COR_BORDA = "#D5DAE0"
COR_TEXTO_SUAVE = "#5B6B7A"

FAMILIA = "Segoe UI"
FAMILIA_FORTE = "Segoe UI Semibold"

# ---------------------------------------------------------------------------
# Forma
# ---------------------------------------------------------------------------
# Raio grande: painéis que ocupam boa parte da tela (a foto da apresentação,
# o botão de entrada). Raio pequeno: cartões e botões, onde 26 arredondaria
# tanto que o retângulo viraria cápsula.
RAIO_CANTO = 26
RAIO_CANTO_PEQUENO = 12

# O topo dos degradês de cabeçalho. O fim é sempre COR_PRIMARIA.
COR_PRIMARIA_ESCURA = "#12314F"

# ---------------------------------------------------------------------------
# Tamanhos de fonte, em pontos para uma tela de 1080px de altura
# ---------------------------------------------------------------------------
TAM_CABECALHO = 27          # "Digite seu nome"
TAM_CABECALHO_SUB = 14
TAM_BUSCA = 30              # o que a pessoa digita
TAM_ALUNO = 22              # cada nome na lista de resultados
TAM_TURMA = 15
TAM_NOME_CONFIRMADO = 58    # a tela verde — o maior texto do sistema
TAM_MENSAGEM = 26
TAM_RODAPE = 11
TAM_CARDAPIO_FAIXA = 15     # o cardápio em letra pequena, no cabeçalho da busca

# Tela de início — vista do outro lado do refeitório, não da fila
TAM_INICIO_NOME = 76
TAM_INICIO_SUB = 19
TAM_INICIO_CARDAPIO_ROTULO = 13
TAM_INICIO_CARDAPIO = 27
TAM_INICIO_CHAMADA = 22

TAM_GESTAO_TITULO = 21
TAM_GESTAO_NUMERO = 48      # quantos pratos preparar
TAM_GESTAO_ROTULO = 12
TAM_GESTAO_BLOCO = 26
TAM_GESTAO_BLOCO_TEXTO = 11
TAM_GESTAO_DETALHE = 14

_fator = 1.0


def nitidez_no_windows() -> None:
    """Desenha em pixels reais em telas com escala (125%, 150%).

    Sem isto o Windows desenha a janela pequena e estica a imagem pronta, e
    todo texto do totem sai borrado. Precisa vir antes do primeiro `tk.Tk()`.
    """
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass  # fora do Windows, ou Windows antigo: fica como sempre foi


def calibrar(root: tk.Misc) -> None:
    """Ajusta a escala das fontes à tela onde o totem está rodando.

    Chamado uma vez, na inicialização. Os limites existem para os dois extremos
    ruins: numa tela pequena demais a interface não pode encolher a ponto de
    ficar ilegível, e numa muito grande não pode virar cartaz de outdoor com
    três nomes na tela.
    """
    global _fator  # noqa: PLW0603
    try:
        altura = root.winfo_screenheight()
    except tk.TclError:
        return
    _fator = max(0.72, min(1.5, altura / 1080))
    # Fontes em ponto crescem com a escala do Windows; os espaçamentos de
    # `px()` não. Fixar 96 dpi faz os dois andarem juntos, e quem escala tudo
    # é o `_fator`, pela altura real da tela.
    root.tk.call("tk", "scaling", 96 / 72)


def fonte(tamanho: int, forte: bool = False) -> tuple[str, int]:
    """Fonte já escalada para a tela atual."""
    familia = FAMILIA_FORTE if forte else FAMILIA
    return (familia, max(8, round(tamanho * _fator)))


def px(valor: int) -> int:
    """Escala uma medida de espaçamento junto com as fontes."""
    return max(1, round(valor * _fator))


# ---------------------------------------------------------------------------
# Helpers de cor (mesma lógica do SIGBEF)
# ---------------------------------------------------------------------------
def ajustar_cor(cor_hex: str, proporcao: float) -> str:
    """Clareia (>1) ou escurece (<1) uma cor #RRGGBB."""
    cor_hex = cor_hex.lstrip("#")
    try:
        r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"#{cor_hex}"
    r, g, b = (max(0, min(255, round(c * proporcao))) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def mesclar_branco(cor_hex: str, proporcao: float) -> str:
    """Desloca a cor em direção ao branco preservando o matiz."""
    cor_hex = cor_hex.lstrip("#")
    try:
        r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"#{cor_hex}"
    r, g, b = (round(c + (255 - c) * proporcao) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


# Os nomes privados ficam como apelido: três módulos já chamavam
# `tema._ajustar_cor`, o que mostra que ele nunca foi privado de verdade.
_ajustar_cor = ajustar_cor
_mesclar_branco = mesclar_branco

COR_PRIMARIA_SUAVE = mesclar_branco(COR_PRIMARIA, 0.72)   # texto sobre a faixa azul
COR_SUCESSO_SUAVE = mesclar_branco(COR_SUCESSO, 0.62)     # texto sobre a tela verde
COR_HOVER_CARD = "#EAF1F9"                                 # nome da lista sob o cursor
COR_SUCESSO_ESCURA = ajustar_cor(COR_SUCESSO, 0.62)        # base do degradê da confirmação


def aplicar_tema(root: tk.Misc) -> None:
    """Configura o pouco de ttk que o totem usa.

    A maior parte da interface é Tk puro: para blocos de cor chapada, um
    `tk.Frame` com `bg` é mais direto e mais previsível do que lutar com os
    estilos do ttk — e cor chapada é a gramática visual inteira aqui.
    """
    calibrar(root)
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COR_FUNDO)

    estilo.configure(".", font=fonte(11), background=COR_FUNDO, foreground=COR_TEXTO)

    # Campo de busca: sem relevo, borda que acende no foco.
    estilo.configure(
        "Busca.TEntry",
        fieldbackground=COR_CARD,
        borderwidth=2,
        relief="solid",
        bordercolor=COR_BORDA,
        lightcolor=COR_CARD,
        darkcolor=COR_CARD,
        insertcolor=COR_DESTAQUE,   # o cursor é o único âmbar da tela de busca
        padding=px(14),
    )
    estilo.map(
        "Busca.TEntry",
        bordercolor=[("focus", COR_SECUNDARIA)],
        lightcolor=[("focus", COR_CARD)],
        darkcolor=[("focus", COR_CARD)],
    )

    estilo.configure(
        "Secundario.TButton",
        font=fonte(12, forte=True),
        background=COR_SECUNDARIA,
        foreground=COR_TEXTO_CLARO,
        borderwidth=0,
        padding=(px(16), px(10)),
    )
    estilo.map(
        "Secundario.TButton",
        background=[
            ("pressed", _ajustar_cor(COR_SECUNDARIA, 0.70)),
            ("active", _ajustar_cor(COR_SECUNDARIA, 0.85)),
        ],
    )
