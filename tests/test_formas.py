"""Testes das primitivas de desenho.

Só o que dá para verificar sem abrir janela. A geometria das telas depende do
Tk ter desenhado de verdade e é conferida rodando o totem — nenhum teste
automatizado deste projeto abre uma janela.

O que **dá** para travar aqui é o contrato que importa mais: o degradê é
opcional e some sem Pillow, em vez de derrubar o totem no meio da fila.
"""
import unittest
from unittest import mock

from siarrn import ui_formas as formas, ui_tema as tema


class TestCor(unittest.TestCase):
    def test_rgb_aceita_com_e_sem_cerquilha(self):
        self.assertEqual(formas.rgb("#1F4E79"), (31, 78, 121))
        self.assertEqual(formas.rgb("1F4E79"), (31, 78, 121))

    def test_as_cores_do_tema_sao_todas_legiveis(self):
        # Uma cor malformada no tema só apareceria na tela da fila.
        for nome in dir(tema):
            if not nome.startswith("COR_"):
                continue
            valor = getattr(tema, nome)
            self.assertRegex(valor, r"^#[0-9A-Fa-f]{6}$", f"{nome} = {valor}")


class TestGradiente(unittest.TestCase):
    def test_tem_o_tamanho_pedido(self):
        imagem = formas.gradiente(60, 40, "#000000", "#FFFFFF")
        self.assertIsNotNone(imagem)
        self.assertEqual(imagem.size, (60, 40))

    def test_vai_de_uma_cor_a_outra(self):
        imagem = formas.gradiente(10, 50, "#000000", "#FFFFFF")
        self.assertEqual(imagem.getpixel((5, 0)), (0, 0, 0))
        self.assertEqual(imagem.getpixel((5, 49)), (255, 255, 255))

    def test_sem_pillow_devolve_nada_em_vez_de_quebrar(self):
        """O totem fica sozinho no refeitório: nada pode levantar exceção.

        Quem chama trata o `None` caindo para cor chapada, e a escola que
        instalar sem Pillow perde só a textura do fundo.
        """
        with mock.patch.object(formas, "PILLOW_DISPONIVEL", False):
            self.assertIsNone(formas.gradiente(60, 40, "#000000", "#FFFFFF"))

    def test_tamanho_invalido_nao_quebra(self):
        # Acontece de verdade: o Tk dispara <Configure> com 1x1 na montagem.
        self.assertIsNone(formas.gradiente(0, 40, "#000000", "#FFFFFF"))
        self.assertIsNone(formas.gradiente(60, 0, "#000000", "#FFFFFF"))


class TestCantoSuave(unittest.TestCase):
    def test_borda_tem_tons_intermediarios(self):
        """Sem tons entre o fundo e a cor, o canto sai em degraus."""
        mascara = formas.mascara_de_canto(12)
        self.assertEqual(mascara.size, (24, 24))
        self.assertEqual(mascara.getpixel((0, 0)), 0)
        self.assertEqual(mascara.getpixel((12, 12)), 255)
        tons = set(mascara.getdata())
        self.assertTrue(any(0 < tom < 255 for tom in tons))


class TestRaios(unittest.TestCase):
    def test_o_tema_define_os_dois_raios(self):
        self.assertGreater(tema.RAIO_CANTO, tema.RAIO_CANTO_PEQUENO)


if __name__ == "__main__":
    unittest.main()
