"""
Testes da regra de previsão.

Este é o módulo mais importante do sistema para testar, porque é o único cuja
correção não depende de banco, rede ou fila: entram números, sai um número.
Os casos abaixo cobrem a promessa central do projeto — que a previsão continua
útil em qualquer nível de adesão às declarações, inclusive zero.
"""
from __future__ import annotations

import unittest

from siarrn import previsao


class TaxaDoAluno(unittest.TestCase):
    def test_usa_historico_proprio_quando_ha_oportunidades_suficientes(self):
        taxa, fallback = previsao.taxa_do_aluno(8, 10, taxa_media=0.5)
        self.assertAlmostEqual(taxa, 0.8)
        self.assertFalse(fallback)

    def test_cai_para_media_da_escola_com_pouco_historico(self):
        """Aluno com uma única oportunidade não 'comparece 100% das vezes'."""
        taxa, fallback = previsao.taxa_do_aluno(1, 1, taxa_media=0.6)
        self.assertAlmostEqual(taxa, 0.6)
        self.assertTrue(fallback)

    def test_aluno_recem_cadastrado_nao_divide_por_zero(self):
        taxa, fallback = previsao.taxa_do_aluno(0, 0, taxa_media=0.6)
        self.assertAlmostEqual(taxa, 0.6)
        self.assertTrue(fallback)

    def test_sem_media_da_escola_assume_presenca(self):
        """Primeiro dia de uso: ninguém tem histórico e a escola também não.

        Errar pra cima quando não se sabe nada é melhor do que mandar preparar
        pouco e faltar comida.
        """
        taxa, fallback = previsao.taxa_do_aluno(0, 0, taxa_media=None)
        self.assertAlmostEqual(taxa, 1.0)
        self.assertTrue(fallback)


class Calculo(unittest.TestCase):
    def test_adesao_total_vira_contagem_exata(self):
        """Todo mundo declarou: não há silencioso, então não há estimativa."""
        resultado = previsao.calcular(sim=80, nao=40, silenciosos=[], taxa_media=0.6)
        self.assertEqual(resultado["previsto"], 80)
        self.assertEqual(resultado["silenciosos"], 0)
        self.assertEqual(resultado["confianca"], "boa")

    def test_adesao_zero_vira_media_historica_pura(self):
        """A promessa central: sem nenhuma declaração, o número ainda é útil.

        Dez alunos que comparecem 70% das vezes → 7 pratos.
        """
        silenciosos = [(7, 10)] * 10
        resultado = previsao.calcular(sim=0, nao=0, silenciosos=silenciosos, taxa_media=0.7)
        self.assertEqual(resultado["previsto"], 7)
        self.assertAlmostEqual(resultado["silenciosos_estimados"], 7.0)

    def test_quem_avisou_ausencia_nao_e_subtraido_de_novo(self):
        """O 'menos não' do documento é conceitual: quem avisou já está fora.

        Se `nao` fosse subtraído do total, este caso daria 5 em vez de 10 — e a
        cozinha prepararia menos da metade do necessário.
        """
        resultado = previsao.calcular(sim=10, nao=5, silenciosos=[], taxa_media=0.6)
        self.assertEqual(resultado["previsto"], 10)
        self.assertEqual(resultado["nao"], 5)

    def test_mistura_declaracoes_com_historico(self):
        """Caso realista: parte declarou, parte ficou em silêncio."""
        silenciosos = [(5, 10), (5, 10), (10, 10), (0, 10)]  # 0.5 + 0.5 + 1.0 + 0.0 = 2.0
        resultado = previsao.calcular(sim=30, nao=8, silenciosos=silenciosos, taxa_media=0.6)
        self.assertAlmostEqual(resultado["silenciosos_estimados"], 2.0)
        self.assertEqual(resultado["previsto"], 32)

    def test_arredonda_para_cima(self):
        """Meio prato não existe, e faltar é pior que sobrar um."""
        resultado = previsao.calcular(sim=0, nao=0, silenciosos=[(1, 10)], taxa_media=0.5)
        self.assertAlmostEqual(resultado["silenciosos_estimados"], 0.1)
        self.assertEqual(resultado["previsto"], 1)

    def test_todos_avisaram_ausencia(self):
        """Feriado, passeio, greve: ninguém almoça e a cozinha não prepara nada."""
        resultado = previsao.calcular(sim=0, nao=120, silenciosos=[], taxa_media=0.6)
        self.assertEqual(resultado["previsto"], 0)

    def test_primeiro_dia_de_uso_conta_todo_mundo(self):
        """Sem histórico nenhum, os 100 silenciosos entram cheios."""
        resultado = previsao.calcular(
            sim=0, nao=0, silenciosos=[(0, 0)] * 100, taxa_media=None
        )
        self.assertEqual(resultado["previsto"], 100)
        self.assertEqual(resultado["confianca"], "sem_dados")


class Confianca(unittest.TestCase):
    def test_sem_dados_quando_a_escola_nao_tem_historico(self):
        resultado = previsao.calcular(0, 0, [(0, 0)], taxa_media=None)
        self.assertEqual(resultado["confianca"], "sem_dados")

    def test_parcial_quando_a_maioria_ainda_usa_a_media(self):
        silenciosos = [(0, 0), (0, 0), (0, 0), (7, 10)]  # 3 de 4 sem histórico
        resultado = previsao.calcular(0, 0, silenciosos, taxa_media=0.6)
        self.assertEqual(resultado["confianca"], "parcial")

    def test_boa_quando_a_estimativa_vem_de_habito_observado(self):
        silenciosos = [(7, 10), (8, 10), (9, 10), (0, 0)]  # só 1 de 4 sem histórico
        resultado = previsao.calcular(0, 0, silenciosos, taxa_media=0.6)
        self.assertEqual(resultado["confianca"], "boa")


if __name__ == "__main__":
    unittest.main()
