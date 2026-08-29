#!/usr/bin/env python3
"""
SIARRN — Gerador dos executáveis

Produz dois programas independentes:

    dist/SIARRN-Servidor/   fica numa máquina da escola, guarda os dados
    dist/SIARRN-Totem/      fica no refeitório, na fila do almoço

São separados de propósito. A máquina do refeitório não precisa carregar o
servidor, e a do servidor não precisa das bibliotecas de câmera e imagem — o
totem passa dos cem megabytes por causa do OpenCV, enquanto o servidor não
chega a vinte.

    python build.py                 gera os dois
    python build.py --servidor      gera só o servidor
    python build.py --totem         gera só o totem
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJETO = Path(__file__).resolve().parent
DIST = PROJETO / "dist"

LEIA_ME = """SIARRN — Totem do refeitório

Para começar
------------
1. Ligue o servidor na máquina que vai guardar os dados (pasta
   SIARRN-Servidor). Ele mostra na tela um endereço parecido com
   http://192.168.0.10:8770 — anote.
2. Abra o SIARRN-Totem.exe nesta pasta. Na primeira vez, informe aquele
   endereço editando o arquivo de configuração descrito abaixo.

As fotos da tela de apresentação
--------------------------------
Ficam na pasta assets/fotos, aqui ao lado. Troque os arquivos por fotos do
refeitório quando tiver — é só copiar para lá. Aceita JPG e PNG, e a ordem é
alfabética.

Configuração desta máquina
--------------------------
Fica em C:/Users/<seu usuário>/.siarrn/totem.json e guarda o endereço do
servidor e o PIN da cozinha (padrão 1234). Troque o PIN antes de deixar o
totem no refeitório.

Painel da cozinha
-----------------
Três toques na linha de informação no rodapé, ou Ctrl+Alt+G, e o PIN.
"""


def rodar(spec: str) -> None:
    print(f"\n=== {spec} ===")
    inicio = time.perf_counter()
    resultado = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", spec],
        cwd=PROJETO,
    )
    if resultado.returncode != 0:
        raise SystemExit(f"falha ao gerar {spec}")
    print(f"    {time.perf_counter() - inicio:.0f}s")


def tamanho(pasta: Path) -> str:
    if not pasta.exists():
        return "—"
    total = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file())
    return f"{total / 1024 / 1024:.0f} MB"


def preparar_totem() -> None:
    """Copia para fora do pacote o que a escola precisa poder editar."""
    destino = DIST / "SIARRN-Totem"
    if not destino.exists():
        return

    fotos_origem = PROJETO / "assets" / "fotos"
    fotos_destino = destino / "assets" / "fotos"
    if fotos_origem.is_dir():
        fotos_destino.parent.mkdir(parents=True, exist_ok=True)
        if fotos_destino.exists():
            shutil.rmtree(fotos_destino)
        shutil.copytree(fotos_origem, fotos_destino)
        print(f"    fotos copiadas para {fotos_destino.relative_to(PROJETO)}")

    (destino / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera os executáveis do SIARRN.")
    parser.add_argument("--servidor", action="store_true", help="gerar só o servidor")
    parser.add_argument("--totem", action="store_true", help="gerar só o totem")
    argumentos = parser.parse_args(argv)

    os_dois = not (argumentos.servidor or argumentos.totem)

    if argumentos.servidor or os_dois:
        rodar("siarrn-servidor.spec")
    if argumentos.totem or os_dois:
        rodar("siarrn-totem.spec")
        preparar_totem()

    print("\nPronto:")
    for nome in ("SIARRN-Servidor", "SIARRN-Totem"):
        pasta = DIST / nome
        if pasta.exists():
            print(f"  dist/{nome:18s} {tamanho(pasta):>8s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
