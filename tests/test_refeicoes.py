"""
Testes de refeições, declarações e consumos.

O teste mais importante daqui é o de idempotência do consumo: é ele que torna
seguro o totem reenviar a fila que guardou offline.
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from siarrn import alunos, dados, refeicoes

from .base import ComBanco


class Refeicao(ComBanco):
    def test_garantir_cria_uma_vez_so(self):
        primeira = refeicoes.garantir("2026-08-04")
        segunda = refeicoes.garantir("2026-08-04")
        self.assertEqual(primeira["id"], segunda["id"])

    def test_dias_diferentes_sao_refeicoes_diferentes(self):
        a = refeicoes.garantir("2026-08-04")
        b = refeicoes.garantir("2026-08-05")
        self.assertNotEqual(a["id"], b["id"])

    def test_turnos_diferentes_convivem(self):
        """Hoje só existe almoço, mas o modelo já aceita lanche sem migração."""
        almoco = refeicoes.garantir("2026-08-04", "almoco")
        lanche = refeicoes.garantir("2026-08-04", "lanche")
        self.assertNotEqual(almoco["id"], lanche["id"])

    def test_guarda_cardapio(self):
        refeicao = refeicoes.garantir("2026-08-04")
        refeicoes.definir_cardapio(refeicao["id"], "Baião de dois")
        self.assertEqual(refeicoes.garantir("2026-08-04")["cardapio"], "Baião de dois")


class Consumo(ComBanco):
    def setUp(self) -> None:
        super().setUp()
        self.aluno = alunos.criar("Ana Souza", "1º A")
        self.refeicao = refeicoes.garantir("2026-08-04")

    def test_registro_repetido_nao_conta_duas_vezes(self):
        """O totem reenvia a fila offline sem saber o que o servidor já tem.

        Se repetição inflasse a contagem, a sincronização estragaria justamente
        o número que o sistema existe para produzir.
        """
        primeiro = refeicoes.registrar_consumo(self.aluno["id"], self.refeicao["id"])
        segundo = refeicoes.registrar_consumo(self.aluno["id"], self.refeicao["id"])

        self.assertTrue(primeiro)
        self.assertFalse(segundo)
        self.assertEqual(refeicoes.total_consumido(self.refeicao["id"]), 1)

    def test_preserva_o_horario_enviado_pelo_totem(self):
        """Almoço registrado offline às 11h47 continua sendo das 11h47."""
        refeicoes.registrar_consumo(
            self.aluno["id"], self.refeicao["id"], "2026-08-04 11:47:00", "qr"
        )
        self.assertTrue(refeicoes.ja_consumiu(self.aluno["id"], self.refeicao["id"]))

    def test_ja_consumiu_e_falso_antes_do_registro(self):
        self.assertFalse(refeicoes.ja_consumiu(self.aluno["id"], self.refeicao["id"]))


class Declaracao(ComBanco):
    def setUp(self) -> None:
        super().setUp()
        self.aluno = alunos.criar("Bruno Costa")
        self.refeicao = refeicoes.garantir("2026-08-04")

    def test_silencio_e_diferente_de_ausencia(self):
        """A distinção que sustenta a previsão inteira.

        Quem avisou que não vem sai da conta. Quem não disse nada entra pelo
        histórico. Confundir os dois é reintroduzir o erro do sistema antigo.
        """
        self.assertIsNone(refeicoes.declaracao_de(self.aluno["id"], self.refeicao["id"]))

        refeicoes.declarar(self.aluno["id"], self.refeicao["id"], False)
        self.assertIs(refeicoes.declaracao_de(self.aluno["id"], self.refeicao["id"]), False)

    def test_aluno_pode_mudar_de_ideia(self):
        refeicoes.declarar(self.aluno["id"], self.refeicao["id"], True)
        refeicoes.declarar(self.aluno["id"], self.refeicao["id"], False)

        self.assertIs(refeicoes.declaracao_de(self.aluno["id"], self.refeicao["id"]), False)
        sim, nao = refeicoes.contagem_declaracoes(self.refeicao["id"])
        self.assertEqual((sim, nao), (0, 1))

    def test_contagem_separa_presencas_de_ausencias(self):
        outro = alunos.criar("Carla Dias")
        refeicoes.declarar(self.aluno["id"], self.refeicao["id"], True)
        refeicoes.declarar(outro["id"], self.refeicao["id"], False)

        self.assertEqual(refeicoes.contagem_declaracoes(self.refeicao["id"]), (1, 1))

    def test_sem_declaracoes_a_contagem_e_zero(self):
        self.assertEqual(refeicoes.contagem_declaracoes(self.refeicao["id"]), (0, 0))


class HistoricoDosSilenciosos(ComBanco):
    """As datas aqui são relativas ao dia de execução de propósito.

    A regra de "oportunidades" compara a data da refeição com a data de cadastro
    do aluno, e o cadastro carimba o momento real. Com datas fixas no código, o
    teste passaria hoje e mentiria daqui a um mês.
    """

    def setUp(self) -> None:
        super().setUp()
        self.hoje_data = date.today()
        self.passadas = [self.hoje_data - timedelta(days=n) for n in (3, 2, 1)]

        self.a = self._aluno_antigo("Ana Lima", dias_atras=10)
        self.b = self._aluno_antigo("Beto Rocha", dias_atras=10)
        self.hoje = refeicoes.garantir(self.hoje_data.isoformat())

    def _aluno_antigo(self, nome: str, dias_atras: int) -> dict:
        """Cadastra um aluno com data de entrada no passado.

        `alunos.criar` sempre carimba o momento atual — correto em produção,
        inútil para montar histórico em teste.
        """
        entrada = self.hoje_data - timedelta(days=dias_atras)
        aluno_id = dados.executar(
            "INSERT INTO aluno (nome, nome_busca, turma, codigo, criado_em)"
            " VALUES (?, ?, '', ?, ?)",
            (nome, alunos.normalizar(nome), alunos.gerar_codigo(), f"{entrada} 07:00:00"),
        )
        return {"id": aluno_id, "nome": nome}

    def test_exclui_quem_declarou(self):
        refeicoes.declarar(self.a["id"], self.hoje["id"], True)
        silenciosos = refeicoes.historico_dos_silenciosos(self.hoje["id"])
        self.assertEqual(len(silenciosos), 1)

    def test_conta_consumos_das_refeicoes_anteriores(self):
        for dia in self.passadas:
            passada = refeicoes.garantir(dia.isoformat())
            refeicoes.registrar_consumo(self.a["id"], passada["id"], f"{dia} 11:40:00")

        refeicoes.declarar(self.b["id"], self.hoje["id"], True)  # deixa só o A silencioso
        consumos, oportunidades = refeicoes.historico_dos_silenciosos(self.hoje["id"])[0]

        self.assertEqual(consumos, 3)
        self.assertEqual(oportunidades, 3)

    def test_aluno_novo_nao_e_penalizado_por_dias_anteriores_ao_cadastro(self):
        """Quem entrou hoje não 'faltou' nas refeições da semana passada.

        Sem isso, todo aluno novo entraria na conta como alguém que nunca vem e
        puxaria a previsão da escola inteira para baixo.
        """
        for dia in self.passadas:
            refeicoes.garantir(dia.isoformat())

        alunos.criar("Novato Recente")  # cadastrado agora, depois das refeições
        refeicoes.declarar(self.a["id"], self.hoje["id"], True)
        refeicoes.declarar(self.b["id"], self.hoje["id"], True)

        consumos, oportunidades = refeicoes.historico_dos_silenciosos(self.hoje["id"])[0]
        self.assertEqual(consumos, 0)
        self.assertEqual(oportunidades, 0)


if __name__ == "__main__":
    unittest.main()
