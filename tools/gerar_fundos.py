#!/usr/bin/env python3
"""
Gera os fundos de demonstração da tela de início.

Existem para que o totem já tenha o que mostrar antes de a escola tirar as
próprias fotos do refeitório. São composições abstratas na paleta do SIGBEF, e
devem ser apagadas assim que houver fotos de verdade — imagem real do lugar
comunica muito mais do que qualquer gradiente.

    python tools/gerar_fundos.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parent.parent / "assets" / "fotos"

LARGURA, ALTURA = 1920, 1080

AZUL_ESCURO = (16, 42, 68)
AZUL = (31, 78, 121)
AZUL_MEDIO = (46, 117, 182)
AMBAR = (242, 169, 0)


def _degrade(de: tuple, para: tuple, inclinado: bool = False) -> Image.Image:
    """Fundo em degradê, desenhado linha a linha.

    Linha a linha em vez de pixel a pixel: são 1080 operações em vez de dois
    milhões, e o resultado é idêntico para um degradê vertical.
    """
    imagem = Image.new("RGB", (LARGURA, ALTURA), de)
    desenho = ImageDraw.Draw(imagem)

    for y in range(ALTURA):
        proporcao = y / ALTURA
        cor = tuple(round(de[i] + (para[i] - de[i]) * proporcao) for i in range(3))
        if inclinado:
            # Desloca o início de cada linha para o degradê descer na diagonal.
            desenho.line([(-LARGURA + y * 1.8, y), (LARGURA, y)], fill=cor, width=2)
        else:
            desenho.line([(0, y), (LARGURA, y)], fill=cor, width=1)

    return imagem


def _camada() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Camada transparente para desenhar formas suaves por cima do degradê."""
    camada = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    return camada, ImageDraw.Draw(camada)


def fundo_diagonais() -> Image.Image:
    """Faixas diagonais largas, no espírito das faixas sólidas do SIGBEF."""
    imagem = _degrade(AZUL_ESCURO, AZUL).convert("RGBA")
    camada, desenho = _camada()

    for indice in range(7):
        deslocamento = indice * 380 - 700
        desenho.polygon(
            [
                (deslocamento, ALTURA),
                (deslocamento + 190, ALTURA),
                (deslocamento + 190 + 620, 0),
                (deslocamento + 620, 0),
            ],
            fill=(*AZUL_MEDIO, 26),
        )

    desenho.polygon(
        [(1180, ALTURA), (1214, ALTURA), (1834, 0), (1800, 0)],
        fill=(*AMBAR, 60),
    )
    return Image.alpha_composite(imagem, camada).convert("RGB")


def fundo_ondas() -> Image.Image:
    """Curvas horizontais largas, mais calmas que as diagonais."""
    imagem = _degrade(AZUL, AZUL_ESCURO).convert("RGBA")
    camada, desenho = _camada()

    for indice in range(4):
        base = 300 + indice * 210
        amplitude = 70 + indice * 18
        pontos = [
            (x, base + math.sin(x / 300 + indice) * amplitude)
            for x in range(0, LARGURA + 20, 20)
        ]
        pontos += [(LARGURA, ALTURA), (0, ALTURA)]
        desenho.polygon(pontos, fill=(*AZUL_MEDIO, 20))

    return Image.alpha_composite(imagem, camada).convert("RGB")


def fundo_grade() -> Image.Image:
    """Grade de pontos com um bloco âmbar deslocado do centro."""
    imagem = _degrade(AZUL_ESCURO, (10, 28, 46)).convert("RGBA")
    camada, desenho = _camada()

    for y in range(80, ALTURA, 76):
        for x in range(80, LARGURA, 76):
            raio = 4 if (x + y) % 152 == 0 else 2
            desenho.ellipse(
                [x - raio, y - raio, x + raio, y + raio],
                fill=(*AZUL_MEDIO, 60),
            )

    desenho.rectangle([1360, 190, 1780, 610], fill=(*AZUL, 70))
    desenho.rectangle([1360, 190, 1780, 202], fill=(*AMBAR, 150))
    return Image.alpha_composite(imagem, camada).convert("RGB")


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)

    fundos = {
        "01-diagonais.jpg": fundo_diagonais,
        "02-ondas.jpg": fundo_ondas,
        "03-grade.jpg": fundo_grade,
    }

    for nome, gerar in fundos.items():
        caminho = DESTINO / nome
        gerar().save(caminho, "JPEG", quality=88, optimize=True)
        print(f"  {nome}  ({caminho.stat().st_size // 1024} KB)")

    print(f"\n{len(fundos)} fundos gerados em {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
