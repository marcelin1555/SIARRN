"""
SIARRN — Registro de acontecimentos

Existe por causa de um defeito real. O servidor registrava cada requisição com
`print`, e quando a saída padrão ficava indisponível — executável empacotado
sem console, redirecionamento fechado, serviço do Windows — o `print` levantava
exceção, matava a thread que atendia a requisição e a conexão fechava sem
resposta. O servidor ficava de pé, escutando na porta, e não respondia nada.

Daí as duas regras deste módulo:

**Registrar nunca pode falhar.** Toda escrita é protegida. Um sistema que cai
porque não conseguiu anotar que algo aconteceu é pior do que um sem registro
nenhum.

**O registro vai para arquivo.** O totem fica sozinho no refeitório e o servidor
numa sala qualquer; não há ninguém olhando um terminal. Quando algo der errado
no meio do almoço, o arquivo é a única forma de descobrir o que foi.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

PASTA = Path.home() / ".siarrn"

# Dois megabytes por arquivo, três de histórico: cobre semanas de almoço e
# nunca vira um arquivo gigante que ninguém consegue abrir.
TAMANHO_MAXIMO = 2 * 1024 * 1024
ARQUIVOS_GUARDADOS = 3

_configurado = False


def configurar(nome: str) -> None:
    """Liga o registro em arquivo. Chamado uma vez, na inicialização.

    `nome` separa os arquivos: o servidor e o totem costumam rodar em máquinas
    diferentes, mas podem estar na mesma.
    """
    global _configurado  # noqa: PLW0603
    if _configurado:
        return
    _configurado = True

    raiz = logging.getLogger("siarrn")
    raiz.setLevel(logging.INFO)
    formato = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")

    try:
        PASTA.mkdir(parents=True, exist_ok=True)
        arquivo = logging.handlers.RotatingFileHandler(
            PASTA / f"{nome}.log",
            maxBytes=TAMANHO_MAXIMO,
            backupCount=ARQUIVOS_GUARDADOS,
            encoding="utf-8",
        )
        arquivo.setFormatter(formato)
        raiz.addHandler(arquivo)
    except OSError:
        # Disco cheio, pasta sem permissão: o programa continua, sem registro.
        pass

    # O console é um bônus, não a base: só entra quando existe de verdade.
    if sys.stdout is not None:
        try:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(formato)
            raiz.addHandler(console)
        except (OSError, ValueError):
            pass


def _emitir(nivel: int, mensagem: str) -> None:
    try:
        logging.getLogger("siarrn").log(nivel, mensagem)
    except Exception:  # noqa: BLE001
        # A regra da casa: registrar jamais derruba quem chamou.
        pass


def info(mensagem: str) -> None:
    _emitir(logging.INFO, mensagem)


def aviso(mensagem: str) -> None:
    _emitir(logging.WARNING, mensagem)


def erro(mensagem: str) -> None:
    _emitir(logging.ERROR, mensagem)


def caminho() -> Path:
    return PASTA
