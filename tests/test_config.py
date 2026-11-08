import tempfile
import unittest
from pathlib import Path
from unittest import mock

from siarrn import config_totem
from siarrn.config_totem import Config


class ConfiguracaoDoTotem(unittest.TestCase):
    def setUp(self) -> None:
        pasta = Path(tempfile.mkdtemp())
        for nome, valor in (("PASTA", pasta), ("ARQUIVO", pasta / "totem.json")):
            remendo = mock.patch.object(config_totem, nome, valor)
            remendo.start()
            self.addCleanup(remendo.stop)

    def test_primeira_vez_nao_esta_salva(self):
        self.assertFalse(Config().salva)

    def test_endereco_sem_http_ganha_http(self):
        """É o que o servidor mostra na tela, e o que alguém vai digitar."""
        config = Config()
        config.servidor = " 192.168.0.10:8770/ "
        self.assertEqual(config.servidor, "http://192.168.0.10:8770")

    def test_endereco_com_esquema_fica_como_esta(self):
        config = Config()
        config.servidor = "https://siarrn.escola.br"
        self.assertEqual(config.servidor, "https://siarrn.escola.br")

    def test_aplicar_salva_e_pin_em_branco_mantem_o_atual(self):
        config = Config()
        config.aplicar("192.168.0.10:8770", "")
        self.assertEqual(config.pin, config_totem.PIN_PADRAO)

        relida = Config()
        self.assertTrue(relida.salva)
        self.assertEqual(relida.servidor, "http://192.168.0.10:8770")

        relida.aplicar("192.168.0.10:8770", "4821")
        self.assertEqual(Config().pin, "4821")


if __name__ == "__main__":
    unittest.main()
