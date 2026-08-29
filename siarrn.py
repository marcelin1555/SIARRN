#!/usr/bin/env python3
"""
SIARRN — Sistema Integrado de Almoço e Refeição

Ponto de entrada do servidor. Sobe a API JSON que o totem (JavaFX) e o app do
aluno (Android) consomem pela rede da escola.

    python siarrn.py                 sobe na porta padrão
    python siarrn.py --porta 9000    escolhe outra porta
    python siarrn.py --seed          popula o banco com alunos fictícios
"""
from __future__ import annotations

import argparse
import sys

from siarrn import __version__, api, dados, log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="siarrn",
        description="Servidor do SIARRN — contagem de almoços da escola.",
    )
    parser.add_argument(
        "--porta", type=int, default=api.PORTA_PADRAO, help="porta do servidor"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="popula o banco com alunos e histórico fictícios, para testes",
    )
    parser.add_argument("--versao", action="version", version=f"SIARRN {__version__}")
    args = parser.parse_args(argv)

    log.configurar("servidor")
    dados.init_db()

    if args.seed:
        from siarrn import seed

        resumo = seed.popular()
        print(
            f"Base de teste criada: {resumo['alunos']} alunos, "
            f"{resumo['refeicoes']} refeições, {resumo['consumos']} consumos."
        )

    try:
        servidor = api.criar_servidor(args.porta)
    except OSError as erro:
        print(f"Não foi possível abrir a porta {args.porta}: {erro}", file=sys.stderr)
        return 1

    print(f"SIARRN {__version__}")
    print(f"  banco:    {dados.DB_PATH}")
    print(f"  endereço: {api.endereco_visivel(args.porta)}")
    print("  Ctrl+C para encerrar.\n")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
