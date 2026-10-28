"""
Testes de cadastro e busca de alunos.

A busca é o que sustenta a fila: se ela falhar com acento, com sobrenome ou
com homônimo, cem pessoas param na frente do totem.
"""
from __future__ import annotations

import unittest

from datetime import date, timedelta

from siarrn import alunos, dados, refeicoes

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


class Mesclagem(ComBanco):
    """O mesmo aluno cadastrado duas vezes na fila.

    O registro abandonado continuaria entrando na previsão pelo hábito antigo
    durante quatro semanas — um prato a mais por duplicata.
    """

    def setUp(self) -> None:
        super().setUp()
        self.dias = [date.today() - timedelta(days=n) for n in (4, 3, 2, 1)]
        self.refeicoes = [refeicoes.garantir(d.isoformat()) for d in self.dias]
        self.hoje = refeicoes.garantir(date.today().isoformat())

        # Cadastro antigo, usado nos dois primeiros dias; depois o aluno não se
        # achou na busca e criou outro, usado nos dois últimos.
        self.velho = self._cadastrar("Joao Pedro Silva", self.dias[0])
        self.novo = self._cadastrar("Jao Pedro", self.dias[2])
        for refeicao, dia in zip(self.refeicoes[:2], self.dias[:2]):
            refeicoes.registrar_consumo(self.velho["id"], refeicao["id"], f"{dia} 11:40:00")
        for refeicao, dia in zip(self.refeicoes[2:], self.dias[2:]):
            refeicoes.registrar_consumo(self.novo["id"], refeicao["id"], f"{dia} 11:40:00")

    def _cadastrar(self, nome: str, dia: date) -> dict:
        codigo = alunos.gerar_codigo()
        aluno_id = dados.executar(
            "INSERT INTO aluno (nome, nome_busca, turma, codigo, criado_em)"
            " VALUES (?, ?, '', ?, ?)",
            (nome, alunos.normalizar(nome), codigo, f"{dia} 07:00:00"),
        )
        return {"id": aluno_id, "codigo": codigo}

    def test_previsao_conta_a_pessoa_uma_vez_so(self):
        self.assertEqual(len(refeicoes.historico_dos_silenciosos(self.hoje["id"])), 2)

        alunos.mesclar(self.velho["id"], self.novo["id"])

        silenciosos = refeicoes.historico_dos_silenciosos(self.hoje["id"])
        self.assertEqual(silenciosos, [(4, 4)])

    def test_data_de_cadastro_vira_a_mais_antiga(self):
        """Ficando com o cadastro novo, os almoços herdados precisam caber nas oportunidades."""
        alunos.mesclar(self.novo["id"], self.velho["id"])
        self.assertEqual(refeicoes.historico_dos_silenciosos(self.hoje["id"]), [(4, 4)])

    def test_mesmo_dia_nos_dois_conta_um_almoco(self):
        refeicoes.registrar_consumo(self.velho["id"], self.hoje["id"], "x")
        refeicoes.registrar_consumo(self.novo["id"], self.hoje["id"], "x")
        alunos.mesclar(self.velho["id"], self.novo["id"])
        self.assertEqual(refeicoes.total_consumido(self.hoje["id"]), 1)

    def test_codigo_antigo_continua_valendo(self):
        alunos.mesclar(self.velho["id"], self.novo["id"])
        achado = alunos.por_codigo(self.novo["codigo"])
        self.assertEqual(achado["id"], self.velho["id"])

    def test_id_antigo_resolve_para_o_que_ficou(self):
        """A fila offline do totem pode trazer o id que já não existe."""
        alunos.mesclar(self.velho["id"], self.novo["id"])
        self.assertEqual(alunos.resolver(self.novo["id"]), self.velho["id"])
        self.assertEqual(alunos.resolver(self.velho["id"]), self.velho["id"])
        self.assertIsNone(alunos.resolver(99999))

    def test_mesclagem_em_cadeia_tem_um_salto(self):
        terceiro = self._cadastrar("J Pedro", self.dias[3])
        alunos.mesclar(self.novo["id"], self.velho["id"])
        alunos.mesclar(terceiro["id"], self.novo["id"])
        self.assertEqual(alunos.resolver(self.velho["id"]), terceiro["id"])
        self.assertEqual(alunos.por_codigo(self.velho["codigo"])["id"], terceiro["id"])

    def test_some_da_lista_e_leva_o_codigo_junto(self):
        alunos.mesclar(self.velho["id"], self.novo["id"])
        lista = alunos.todos()
        self.assertEqual([a["id"] for a in lista], [self.velho["id"]])
        self.assertEqual(lista[0]["codigos_antigos"], self.novo["codigo"])

    def test_recusa_o_mesmo_cadastro_e_o_ja_mesclado(self):
        with self.assertRaises(ValueError):
            alunos.mesclar(self.velho["id"], self.velho["id"])
        alunos.mesclar(self.velho["id"], self.novo["id"])
        with self.assertRaises(ValueError):
            alunos.mesclar(self.velho["id"], self.novo["id"])



class BancoAntigo(ComBanco):
    def test_ganha_a_coluna_de_mesclagem_sem_perder_alunos(self):
        """Banco criado antes da mesclagem existir: a escola não pode perder o histórico."""
        with dados.db_cursor() as cur:
            cur.executescript(
                "PRAGMA foreign_keys = OFF;"
                "CREATE TABLE aluno_antigo AS SELECT id, nome, nome_busca, turma, codigo,"
                " ativo, criado_em FROM aluno;"
                "DROP TABLE aluno; ALTER TABLE aluno_antigo RENAME TO aluno;"
                "INSERT INTO aluno VALUES (1, 'Ana', 'ana', '', 'ABCDEFGH', 1, '2026-08-01');"
            )
        dados.init_db()
        self.assertEqual(alunos.todos()[0]["nome"], "Ana")
        self.assertEqual(alunos.resolver(1), 1)


if __name__ == "__main__":
    unittest.main()
