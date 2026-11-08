#!/usr/bin/env python3
"""
Gera a marca do SIARRN: símbolo, logo, ícone do Windows e ícones do Android.

O símbolo é um prato visto de cima com uma contagem de cinco dentro — quatro
riscos e um corte. São as duas coisas que o sistema faz: almoço e conta. A
contagem em traços é a mesma do painel da cozinha, que veio do papel onde se
contava antes.

Uma geometria só, em unidades de 0 a 100, desenha tudo. Mudou a marca, roda de
novo e todos os arquivos saem iguais entre si:

    python tools/gerar_marca.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "assets" / "marca"
ANDROID = RAIZ / "app-aluno" / "app" / "src" / "main" / "res"

# Paleta do SIGBEF (sigbef/ui_tema.py), a mesma de siarrn/ui_tema.py.
AZUL = "#1F4E79"
AZUL_CLARO = "#2E75B6"
AMBAR = "#F2A900"
BRANCO = "#FFFFFF"
BORDA = "#D5DAE0"
TEXTO_SUAVE = "#5B6573"

FONTE_FORTE = Path("C:/Windows/Fonts/seguisb.ttf")
FONTE = Path("C:/Windows/Fonts/segoeui.ttf")

# Desenhado neste múltiplo e reduzido: é a redução que suaviza as bordas.
SUPER = 8


def _geometria(pequeno: bool) -> dict:
    """As medidas do símbolo, de 0 a 100.

    Abaixo de 48 px, quatro riscos finos viram uma mancha. A versão pequena
    troca por três riscos grossos e tira o filete da aba do prato: perde a
    contagem exata, mas continua se lendo como prato com riscos.
    """
    if pequeno:
        return {"riscos": (37, 50, 63), "largura": 8.5, "topo": 36, "base": 64,
                "corte": ((30, 58.5), (70, 41.5)), "largura_corte": 8, "aba": False}
    return {"riscos": (37.5, 45.8, 54.2, 62.5), "largura": 5.4, "topo": 37, "base": 63,
            "corte": ((31, 57.5), (69, 42.5)), "largura_corte": 6, "aba": True}


def simbolo(tamanho: int, forma: str = "quadrado") -> Image.Image:
    """O símbolo em PNG. `forma` é "quadrado" (cantos arredondados) ou "circulo"."""
    g = _geometria(tamanho < 48)
    lado = tamanho * SUPER
    u = lado / 100
    imagem = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(imagem)

    if forma == "circulo":
        d.ellipse([0, 0, lado - 1, lado - 1], fill=AZUL)
    else:
        d.rounded_rectangle([0, 0, lado - 1, lado - 1], radius=22 * u, fill=AZUL)

    d.ellipse(_caixa(50, 50, 36, u), fill=BRANCO)
    if g["aba"]:
        d.ellipse(_caixa(50, 50, 28, u), outline=BORDA, width=round(1.6 * u))

    meia = g["largura"] / 2
    for x in g["riscos"]:
        d.rounded_rectangle([(x - meia) * u, g["topo"] * u, (x + meia) * u, g["base"] * u],
                            radius=meia * u, fill=AZUL)
    _linha_arredondada(d, g["corte"], g["largura_corte"], u, AMBAR)

    return imagem.resize((tamanho, tamanho), Image.LANCZOS)


def _caixa(cx: float, cy: float, raio: float, u: float) -> list[float]:
    return [(cx - raio) * u, (cy - raio) * u, (cx + raio) * u, (cy + raio) * u]


def _linha_arredondada(d, pontos, largura, u, cor) -> None:
    (x1, y1), (x2, y2) = pontos
    d.line([(x1 * u, y1 * u), (x2 * u, y2 * u)], fill=cor, width=round(largura * u))
    for x, y in pontos:
        d.ellipse(_caixa(x, y, largura / 2, u), fill=cor)


def simbolo_svg() -> str:
    """O mesmo símbolo em vetor, para o README e para quem quiser ampliar."""
    g = _geometria(False)
    meia = g["largura"] / 2
    riscos = "\n".join(
        f'  <rect x="{x - meia:g}" y="{g["topo"]}" width="{g["largura"]:g}" '
        f'height="{g["base"] - g["topo"]}" rx="{meia:g}" fill="{AZUL}"/>'
        for x in g["riscos"]
    )
    (x1, y1), (x2, y2) = g["corte"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="512" height="512">
  <title>SIARRN</title>
  <rect width="100" height="100" rx="22" fill="{AZUL}"/>
  <circle cx="50" cy="50" r="36" fill="{BRANCO}"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="{BORDA}" stroke-width="1.6"/>
{riscos}
  <line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{AMBAR}" stroke-width="{g["largura_corte"]}" stroke-linecap="round"/>
</svg>
"""


def logo(altura: int, cor_nome: str, cor_frase: str) -> Image.Image:
    """Símbolo à esquerda, nome e frase à direita. Fundo transparente."""
    nome_fonte = ImageFont.truetype(str(FONTE_FORTE), round(altura * 0.52))
    frase_fonte = ImageFont.truetype(str(FONTE), round(altura * 0.17))
    nome, frase = "SIARRN", "Sistema Integrado de Almoço e Refeição"

    medir = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    largura_texto = max(medir.textlength(nome, font=nome_fonte),
                        medir.textlength(frase, font=frase_fonte))
    respiro = round(altura * 0.22)
    imagem = Image.new("RGBA", (altura + respiro + round(largura_texto) + 4, altura), (0, 0, 0, 0))
    imagem.alpha_composite(simbolo(altura))

    d = ImageDraw.Draw(imagem)
    x = altura + respiro
    d.text((x, altura * 0.47), nome, font=nome_fonte, fill=cor_nome, anchor="ls")
    d.text((x, altura * 0.80), frase, font=frase_fonte, fill=cor_frase, anchor="ls")
    return imagem


def capa(largura: int = 1280, altura: int = 640) -> Image.Image:
    """Imagem de apresentação do repositório (Settings → Social preview)."""
    imagem = Image.new("RGBA", (largura, altura), AZUL)
    marca = logo(220, BRANCO, "#C9D8E8")
    imagem.alpha_composite(marca, ((largura - marca.width) // 2, (altura - marca.height) // 2))
    ImageDraw.Draw(imagem).rectangle([0, altura - 14, largura, altura], fill=AMBAR)
    return imagem.convert("RGB")


def main() -> int:
    MARCA.mkdir(parents=True, exist_ok=True)

    (MARCA / "simbolo.svg").write_text(simbolo_svg(), encoding="utf-8")
    simbolo(512).save(MARCA / "simbolo-512.png")
    logo(160, AZUL, TEXTO_SUAVE).save(MARCA / "logo-claro.png")
    logo(160, BRANCO, "#C9D8E8").save(MARCA / "logo-escuro.png")
    capa().save(MARCA / "capa-github.png")

    # Cada tamanho desenhado no próprio tamanho: o Windows escolhe o que
    # cabe, e um 256 reduzido para 16 viraria borrão.
    tamanhos = [16, 24, 32, 48, 64, 128, 256]
    icones = [simbolo(t) for t in tamanhos]
    icones[-1].save(RAIZ / "assets" / "siarrn.ico", sizes=[(t, t) for t in tamanhos],
                    append_images=icones[:-1])

    for pasta, lado in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                        ("xxhdpi", 144), ("xxxhdpi", 192)):
        destino = ANDROID / f"mipmap-{pasta}"
        simbolo(lado).save(destino / "ic_launcher.png")
        simbolo(lado, "circulo").save(destino / "ic_launcher_round.png")

    print(f"marca gerada em {MARCA.relative_to(RAIZ)}, assets/siarrn.ico e mipmaps do app")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
