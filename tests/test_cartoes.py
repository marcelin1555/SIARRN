"""
Testes dos cartões com QR.

O teste central é o de ida e volta: o QR desenhado no cartão precisa ser lido de
volta como o código daquele aluno. Se essa cadeia quebrar, os cartões impressos
viram papel inútil — e o erro só apareceria no dia em que a escola já tivesse
distribuído cento e vinte deles.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from siarrn import cartoes

try:
    import cv2
    import numpy as np
    LEITOR_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende do ambiente
    LEITOR_DISPONIVEL = False


def _ler_qr(imagem) -> str:
    cinza = cv2.cvtColor(np.array(imagem), cv2.COLOR_RGB2GRAY)
    texto, _, _ = cv2.QRCodeDetector().detectAndDecode(cinza)
    return texto


ALUNO = {"id": 1, "nome": "Ana Ribeiro Moura", "turma": "3º A", "codigo": "WN6SKJ49"}


class Geracao(unittest.TestCase):
    def test_qr_sai_no_tamanho_pedido(self):
        self.assertEqual(cartoes.gerar_qr("ABC12345", 200).size, (200, 200))

    def test_cartao_sai_no_tamanho_pedido(self):
        self.assertEqual(cartoes.desenhar_cartao(ALUNO, 620, 400).size, (620, 400))

    def test_folhas_respeitam_a_capacidade_da_pagina(self):
        por_pagina = cartoes.por_pagina()
        alunos = [dict(ALUNO, id=i, codigo=f"COD{i:05d}") for i in range(por_pagina * 2 + 1)]
        self.assertEqual(len(cartoes.gerar_folhas(alunos)), 3)

    def test_uma_pagina_para_poucos_alunos(self):
        self.assertEqual(len(cartoes.gerar_folhas([ALUNO])), 1)

    def test_sem_alunos_nao_gera_pdf(self):
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ValueError):
                cartoes.gerar_pdf([], Path(pasta) / "vazio.pdf")

    def test_pdf_e_criado(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = cartoes.gerar_pdf([ALUNO], Path(pasta) / "cartoes.pdf")
            self.assertTrue(destino.is_file())
            self.assertGreater(destino.stat().st_size, 0)


class NomeNoCartao(unittest.TestCase):
    """O nome tem que caber inteiro.

    É por ele que alguém separa o cartão certo para o aluno certo na hora de
    entregar. "Ana Ribeir…" não serve para nada.
    """

    @staticmethod
    def _acomodar(nome: str, largura: int = 300):
        from PIL import Image, ImageDraw
        desenho = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        return cartoes._acomodar_nome(nome, desenho, largura, 40)

    def test_nome_curto_fica_em_uma_linha(self):
        linhas, _ = self._acomodar("Ana Lima")
        self.assertEqual(len(linhas), 1)

    def test_nome_longo_quebra_em_duas_linhas_sem_perder_nada(self):
        nome = "Alice Pereira Nascimento"
        linhas, _ = self._acomodar(nome)

        self.assertLessEqual(len(linhas), 2)
        self.assertEqual(" ".join(linhas), nome)
        self.assertNotIn("…", " ".join(linhas))

    def test_nome_muito_longo_ainda_cabe(self):
        nome = "Maria Aparecida da Conceição Cavalcante de Albuquerque"
        linhas, _ = self._acomodar(nome)
        self.assertTrue(linhas)
        self.assertTrue(all(linha for linha in linhas))


@unittest.skipUnless(LEITOR_DISPONIVEL, "OpenCV não instalado")
class IdaEVolta(unittest.TestCase):
    def test_qr_do_cartao_devolve_o_codigo_do_aluno(self):
        cartao = cartoes.desenhar_cartao(ALUNO, 620, 400)
        self.assertEqual(_ler_qr(cartao), ALUNO["codigo"])

    def test_alunos_diferentes_geram_qr_diferentes(self):
        outro = dict(ALUNO, codigo="Y6QS5CDF", nome="Bruno Costa")
        self.assertNotEqual(
            _ler_qr(cartoes.desenhar_cartao(ALUNO, 620, 400)),
            _ler_qr(cartoes.desenhar_cartao(outro, 620, 400)),
        )

    def test_le_mesmo_com_o_cartao_pequeno_torto_e_fora_de_foco(self):
        """O caso real: cartão amassado no bolso, mostrado de qualquer jeito."""
        cartao = cartoes.desenhar_cartao(ALUNO, 620, 400)
        cinza = cv2.cvtColor(np.array(cartao), cv2.COLOR_RGB2GRAY)

        folga = 120
        com_folga = cv2.copyMakeBorder(
            cinza, folga, folga, folga, folga, cv2.BORDER_CONSTANT, value=255
        )
        centro = (com_folga.shape[1] // 2, com_folga.shape[0] // 2)
        girado = cv2.warpAffine(
            com_folga, cv2.getRotationMatrix2D(centro, 14, 1.0),
            (com_folga.shape[1], com_folga.shape[0]), borderValue=255,
        )
        pequeno = cv2.resize(girado, (420, 300), interpolation=cv2.INTER_AREA)
        borrado = cv2.GaussianBlur(pequeno, (3, 3), 0)

        texto, _, _ = cv2.QRCodeDetector().detectAndDecode(borrado)
        self.assertEqual(texto, ALUNO["codigo"])


if __name__ == "__main__":
    unittest.main()
