"""
SIARRN — Cartões com QR para impressão

Gera uma folha A4 de cartões para recortar, cada um com o QR do aluno, o nome e
a turma. Papel comum resolve: o cartão custa centavos e, se perder, imprime
outro. A escola não precisa comprar leitor, crachá nem impressora especial.

O mesmo código funciona impresso e na tela do celular, então quem tem aparelho
não precisa de papel — e quem não tem não fica de fora. Quem esquecer os dois
continua achando o próprio nome no totem.

Decisões que vieram de medição, não de gosto
--------------------------------------------
**Correção de erro H (30%).** Um código de oito caracteres cabe na versão 1 do
QR mesmo no nível mais alto de correção, então a robustez extra sai de graça —
não aumenta o tamanho do desenho nem a densidade dos módulos.

**Margem de 4 módulos.** É a "quiet zone" exigida pelo padrão. Testando com 2,
a leitura falhava com o cartão inclinado ou distante; com 4, passa em todos os
cenários simulados, inclusive longe, torto e fora de foco.
"""
from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from . import ui_tema as tema

# 150 pontos por polegada: suficiente para QR e texto em papel comum, e leve o
# bastante para gerar doze páginas em segundos numa máquina modesta.
DPI = 150
A4 = (int(8.27 * DPI), int(11.69 * DPI))

MARGEM = int(0.4 * DPI)
COLUNAS, LINHAS = 2, 5

NIVEL_CORRECAO = qrcode.constants.ERROR_CORRECT_H
MARGEM_QR = 4

_FONTES = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
_FONTES_LEVES = (
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _fonte(tamanho: int, forte: bool = False):
    """Carrega uma fonte do sistema, caindo na embutida se nenhuma existir."""
    for caminho in (_FONTES if forte else _FONTES_LEVES):
        if Path(caminho).is_file():
            try:
                return ImageFont.truetype(caminho, tamanho)
            except OSError:
                continue
    return ImageFont.load_default()


def gerar_qr(codigo: str, lado: int) -> Image.Image:
    """Desenha o QR de um código, já no tamanho pedido."""
    qr = qrcode.QRCode(
        error_correction=NIVEL_CORRECAO,
        box_size=10,
        border=MARGEM_QR,
    )
    qr.add_data(codigo)
    qr.make(fit=True)

    imagem = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # NEAREST de propósito: suavizar as bordas dos módulos é exatamente o que
    # atrapalha a leitura. O QR tem que sair do papel com transições secas.
    return imagem.resize((lado, lado), Image.NEAREST)


def _acomodar_nome(nome: str, desenho, largura: int, tamanho_maximo: int):
    """Encaixa o nome inteiro no espaço, sem cortar.

    O nome é o que permite entregar o cartão certo ao aluno certo — truncar
    "Ana Ribeiro Cavalcante" em "Ana Ribeir…" derrota o propósito de imprimir
    o nome. Então, em vez de cortar, tenta em uma linha; não cabendo, quebra em
    duas; e só então vai diminuindo a fonte.

    Devolve `(linhas, fonte)`.
    """
    palavras = nome.split()

    for tamanho in range(tamanho_maximo, max(8, tamanho_maximo - 14), -1):
        fonte = _fonte(tamanho, forte=True)

        if desenho.textlength(nome, font=fonte) <= largura:
            return [nome], fonte

        # Quebra no ponto que deixa as duas linhas mais parecidas, para o bloco
        # não sair com uma linha cheia e outra com uma palavra solta.
        if len(palavras) > 1:
            melhor = None
            for corte in range(1, len(palavras)):
                primeira = " ".join(palavras[:corte])
                segunda = " ".join(palavras[corte:])
                maior = max(
                    desenho.textlength(primeira, font=fonte),
                    desenho.textlength(segunda, font=fonte),
                )
                if maior <= largura and (melhor is None or maior < melhor[0]):
                    melhor = (maior, [primeira, segunda])
            if melhor is not None:
                return melhor[1], fonte

    # Nome absurdamente longo: aí sim encurta, no menor tamanho.
    fonte = _fonte(max(8, tamanho_maximo - 14), forte=True)
    texto = nome
    while texto and desenho.textlength(texto + "…", font=fonte) > largura:
        texto = texto[:-1]
    return [texto.rstrip() + "…"], fonte


def desenhar_cartao(aluno: dict, largura: int, altura: int) -> Image.Image:
    """Um cartão: QR à esquerda, identificação à direita."""
    cartao = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(cartao)

    # Faixa âmbar na lateral: a mesma marca de destaque do SIGBEF, e ajuda a
    # separar visualmente os cartões depois de recortados.
    desenho.rectangle([0, 0, int(largura * 0.018), altura], fill=tema.COR_DESTAQUE)

    # O QR encolheu em relação ao primeiro desenho para o nome ganhar largura:
    # ele já é lido de longe e torto no tamanho atual, então o espaço extra
    # rende mais no texto do que no código.
    lado_qr = int(altura * 0.62)
    recuo = int(altura * 0.12)
    cartao.paste(gerar_qr(aluno["codigo"], lado_qr), (recuo, int((altura - lado_qr) / 2)))

    x = recuo + lado_qr + int(largura * 0.045)
    largura_texto = largura - x - int(largura * 0.04)

    linhas, fonte_nome = _acomodar_nome(
        aluno.get("nome", ""), desenho, largura_texto, int(altura * 0.115)
    )
    fonte_turma = _fonte(int(altura * 0.082))
    fonte_codigo = _fonte(int(altura * 0.060))
    fonte_rodape = _fonte(int(altura * 0.055))

    altura_linha = int(altura * 0.125)
    y = recuo + int(altura * 0.04)
    for linha in linhas:
        desenho.text((x, y), linha, font=fonte_nome, fill=tema.COR_TEXTO)
        y += altura_linha

    y += int(altura * 0.02)
    turma = (aluno.get("turma") or "").strip()
    if turma:
        desenho.text((x, y), turma, font=fonte_turma, fill=tema.COR_TEXTO_SUAVE)
        y += int(altura * 0.13)

    # O código escrito por extenso: se o QR ficar ilegível de tanto uso, ainda
    # dá para digitá-lo no modo gestão.
    desenho.text((x, y), aluno["codigo"], font=fonte_codigo, fill=tema.COR_SECUNDARIA)

    desenho.text(
        (x, altura - recuo - int(altura * 0.06)),
        "SIARRN · almoço", font=fonte_rodape, fill=tema.COR_TEXTO_SUAVE,
    )

    desenho.rectangle([0, 0, largura - 1, altura - 1], outline="#C9CFD6", width=1)
    return cartao


def gerar_folhas(alunos: list[dict]) -> list[Image.Image]:
    """Distribui os alunos em páginas A4 de cartões."""
    largura = (A4[0] - MARGEM * 2) // COLUNAS
    altura = (A4[1] - MARGEM * 2) // LINHAS
    por_pagina = COLUNAS * LINHAS

    paginas = []
    for inicio in range(0, len(alunos), por_pagina):
        pagina = Image.new("RGB", A4, "white")
        lote = alunos[inicio:inicio + por_pagina]

        for posicao, aluno in enumerate(lote):
            coluna, linha = posicao % COLUNAS, posicao // COLUNAS
            pagina.paste(
                desenhar_cartao(aluno, largura, altura),
                (MARGEM + coluna * largura, MARGEM + linha * altura),
            )
        paginas.append(pagina)

    return paginas


def gerar_pdf(alunos: list[dict], destino: Path) -> Path:
    """Escreve o PDF com todos os cartões. Devolve o caminho gerado."""
    if not alunos:
        raise ValueError("Nenhum aluno para gerar cartões.")

    paginas = gerar_folhas(alunos)
    destino.parent.mkdir(parents=True, exist_ok=True)
    paginas[0].save(
        destino, "PDF", resolution=DPI, save_all=True, append_images=paginas[1:]
    )
    return destino


def por_pagina() -> int:
    return COLUNAS * LINHAS
