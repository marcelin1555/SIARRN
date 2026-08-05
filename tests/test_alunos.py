"""
Testes de cadastro e busca de alunos.

A busca é o que sustenta a fila: se ela falhar com acento, com sobrenome ou
com homônimo, cem pessoas param na frente do totem.
"""
from __future__ import annotations

import unittest

from siarrn import alunos

from .base import ComBanco


class Normalizacao(unittest.TestCase):
    def test_remove_acento_e_caixa(self):
        self.assertEqual(alunos.normalizar("João"), "joao")
        self.assertEqual(alunos.normalizar("JÚLIA"), "julia")
        self.assertEqual(alunos.normalizar("Conceição"), "conceicao")

    def test_colapsa_espacos(self):
        self.assertEqual(alunos.normalizar("  Ana   Maria  "), "ana maria")


class Codigo(unittest.TestCase):
    def test_nao_usa_caracteres_ambiguos(self):
        """0/O e 1/I/L viram erro de digitação quando o código é lido do papel."""
        for _ in range(200):
            codigo = alunos.gerar_codigo()
            self.assertFalse(set(codigo) & set("01OIL"))

    def test_tem_tamanho_fixo(self):
        self.assertEqual(len(alunos.gerar_codigo()), 8)


class Cadastro(ComBanco):
    def test_cria_e_devolve_codigo(self):
        aluno = alunos.criar("Maria Silva", "2º A")
        self.assertEqual(aluno["nome"], "Maria Silva")
        self.assertEqual(aluno["turma"], "2º A")
        self.assertEqual(len(aluno["codigo"]), 8)

    def test_codigos_sao_unicos(self):
        codigos = {alunos.criar(f"Aluno {i}")["codigo"] for i in range(100)}
        self.assertEqual(len(codigos), 100)

    def test_recusa_nome_vazio(self):
        with self.assertRaises(ValueError):
            alunos.criar("   ")

    def test_permite_homonimos(self):
        """Dois 'João Silva' existem de verdade e o cadastro não pode travar."""
        a = alunos.criar("João Silva", "1º A")
        b = alunos.criar("João Silva", "3º B")
        self.assertNotEqual(a["id"], b["id"])

    def test_renomear_atualiza_a_busca(self):
        aluno = alunos.criar("Jõao Silva")
        alunos.renomear(aluno["id"], "João Silva")
        self.assertTrue(alunos.buscar("joao"))


class Busca(ComBanco):
    def setUp(self) -> None:
        super().setUp()
        for nome, turma in [
            ("João Silva", "1º A"),
            ("João Souza", "2º B"),
            ("Júlia Medeiros", "1º A"),
            ("Ana Silveira", "3º A"),
            ("Basílio Nunes", "2º A"),
            ("Maria Conceição", "1º B"),
        ]:
            alunos.criar(nome, turma)

    def _nomes(self, termo: str) -> list[str]:
        return [a["nome"] for a in alunos.buscar(termo)]

    def test_encontra_ignorando_acento(self):
        self.assertIn("Júlia Medeiros", self._nomes("jul"))
        self.assertIn("Maria Conceição", self._nomes("concei"))

    def test_encontra_ignorando_caixa(self):
        self.assertIn("João Silva", self._nomes("JOAO"))

    def test_encontra_pelo_sobrenome(self):
        encontrados = self._nomes("sil")
        self.assertIn("João Silva", encontrados)
        self.assertIn("Ana Silveira", encontrados)

    def test_nao_casa_no_meio_da_palavra(self):
        """'sil' não pode trazer 'Basílio' — encheria a tela de gente errada."""
        self.assertNotIn("Basílio Nunes", self._nomes("sil"))

    def test_termo_curto_devolve_vazio(self):
        """Uma letra traria meia escola; o totem exige pelo menos duas."""
        self.assertEqual(alunos.buscar("j"), [])

    def test_homonimos_vem_com_turma_para_desambiguar(self):
        for aluno in alunos.buscar("joao"):
            self.assertTrue(aluno["turma"])

    def test_respeita_o_limite(self):
        for i in range(40):
            alunos.criar(f"Carlos Teste {i}")
        self.assertEqual(len(alunos.buscar("carlos", limite=5)), 5)


class PorCodigo(ComBanco):
    def test_encontra_em_qualquer_caixa(self):
        aluno = alunos.criar("Pedro Lima")
        self.assertIsNotNone(alunos.por_codigo(aluno["codigo"].lower()))
        self.assertIsNotNone(alunos.por_codigo(f"  {aluno['codigo']}  "))

    def test_codigo_inexistente_devolve_none(self):
        self.assertIsNone(alunos.por_codigo("ZZZZZZZZ"))


if __name__ == "__main__":
    unittest.main()
