"""
SIARRN — Tema visual

A paleta é a mesma do SIGBEF, com os valores copiados de `sigbef/ui_tema.py`
sem aproximação. Os dois sistemas são apresentados juntos na escola e precisam
parecer da mesma família; se um dia a paleta do SIGBEF mudar, é aqui que se
mexe.

O vocabulário de cor também é herdado, com os mesmos significados do terminal
de autoatendimento da biblioteca: **verde é ação positiva, laranja é atenção,
azul é informação**. Quem já usa o SIGBEF lê o SIARRN sem aprender nada novo.

Regras de forma, também do SIGBEF: blocos de cor chapada, sem cantos
arredondados, sem sombra, sem gradiente.

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

TAM_GESTAO_TITULO = 21
TAM_GESTAO_NUMERO = 56      # quantos pratos preparar
TAM_GESTAO_ROTULO = 12
TAM_GESTAO_BLOCO = 26
TAM_GESTAO_BLOCO_TEXTO = 11
TAM_GESTAO_DETALHE = 14

_fator = 1.0


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
def _ajustar_cor(cor_hex: str, proporcao: float) -> str:
    """Clareia (>1) ou escurece (<1) uma cor #RRGGBB."""
    cor_hex = cor_hex.lstrip("#")
    try:
        r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"#{cor_hex}"
    r, g, b = (max(0, min(255, round(c * proporcao))) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _mesclar_branco(cor_hex: str, proporcao: float) -> str:
    """Desloca a cor em direção ao branco preservando o matiz."""
    cor_hex = cor_hex.lstrip("#")
    try:
        r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"#{cor_hex}"
    r, g, b = (round(c + (255 - c) * proporcao) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


COR_PRIMARIA_SUAVE = _mesclar_branco(COR_PRIMARIA, 0.72)   # texto sobre a faixa azul
COR_SUCESSO_SUAVE = _mesclar_branco(COR_SUCESSO, 0.62)     # texto sobre a tela verde
COR_HOVER_CARD = "#EAF1F9"                                  # nome da lista sob o cursor


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
