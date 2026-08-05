"""Base comum dos testes que precisam de banco."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from siarrn import dados


class ComBanco(unittest.TestCase):
    """Cada teste roda contra um SQLite temporário e descartável.

    Sem isso, um teste que apagasse dados encostaria no banco real da escola —
    que é o mesmo arquivo que o servidor usa em produção.
    """

    def setUp(self) -> None:
        self._pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        dados.usar_banco(Path(self._pasta.name) / "teste.db")
        dados.init_db()

    def tearDown(self) -> None:
        self._pasta.cleanup()
