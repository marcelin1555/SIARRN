"""
SIARRN — Configuração da máquina onde o totem está instalado.

Fica em `~/.siarrn/totem.json` porque é informação do equipamento, não do
projeto: o endereço do servidor e o PIN da cozinha mudam de escola para escola
e não podem viver dentro do código.

A mesma pasta guarda a cópia local dos alunos e a fila de almoços pendentes.
"""
from __future__ import annotations

from . import log

import json
import sys
from pathlib import Path


def pasta_do_programa() -> Path:
    """Onde ficam os arquivos que a escola pode trocar — hoje, as fotos.

    Empacotado, `__file__` aponta para dentro de uma pasta temporária que o
    PyInstaller descompacta a cada execução: qualquer coisa gravada ali some, e
    o que está ali dentro não pode ser editado por quem usa. As fotos precisam
    ficar **ao lado do executável**, senão trocá-las exigiria recompilar o
    programa — e a escola não vai recompilar nada.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


PASTA = Path.home() / ".siarrn"
ARQUIVO = PASTA / "totem.json"

SERVIDOR_PADRAO = "http://localhost:8770"
PIN_PADRAO = "1234"


class Config:
    def __init__(self) -> None:
        self._valores: dict = {}
        self._carregar()

    def _carregar(self) -> None:
        if not ARQUIVO.is_file():
            return
        try:
            self._valores = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            log.aviso(f"Configuração ilegível, usando os padrões: {erro}")

    def salvar(self) -> None:
        try:
            PASTA.mkdir(parents=True, exist_ok=True)
            ARQUIVO.write_text(
                json.dumps(self._valores, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as erro:
            log.aviso(f"Não foi possível salvar a configuração: {erro}")

    # -- servidor ----------------------------------------------------------
    @property
    def servidor(self) -> str:
        return self._valores.get("servidor", SERVIDOR_PADRAO)

    @servidor.setter
    def servidor(self, url: str) -> None:
        url = url.strip().rstrip("/")
        # Quem instala digita o que o servidor mostra na tela, "192.168.0.10:8770".
        # Sem o esquema, o urlsplit não acha o host e o totem iria para localhost.
        if url and "://" not in url:
            url = "http://" + url
        self._valores["servidor"] = url

    @property
    def salva(self) -> bool:
        """Falso só na primeira vez que o programa abre nesta máquina."""
        return ARQUIVO.is_file()

    def aplicar(self, servidor: str, pin: str) -> None:
        """O que a tela "Este totem" devolve. PIN em branco mantém o atual."""
        self.servidor = servidor
        if pin.strip():
            self.pin = pin
        self.salvar()

    # -- gestão ------------------------------------------------------------
    @property
    def pin(self) -> str:
        """PIN de entrada no modo gestão.

        Não é segurança de verdade — quem tem acesso à máquina lê o arquivo. O
        que ele evita é o cenário real: o totem sozinho na fila, com cem
        adolescentes por perto e o painel da cozinha a um toque de distância.
        """
        return str(self._valores.get("pin", PIN_PADRAO))

    @pin.setter
    def pin(self, valor: str) -> None:
        self._valores["pin"] = valor.strip()

    # -- token da API ------------------------------------------------------
    @property
    def token(self) -> str:
        """Vazio significa que a escola não configurou token nenhum."""
        return self._valores.get("token", "")

    @token.setter
    def token(self, valor: str) -> None:
        self._valores["token"] = valor.strip()
