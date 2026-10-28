"""
Testes da base local e da fila offline do totem.

O teste mais importante daqui é `BuscaBateComOServidor`. Ele existe porque o
totem era em Java, com a regra de busca escrita numa segunda linguagem — e uma
divergência entre as duas faria um aluno cadastrado pelo servidor sumir da tela
do totem, aparecendo só na frente da fila do almoço. Depois da migração as duas
buscas usam `texto.combina`, e este teste é o que garante que a versão em SQL
continua concordando com a versão em Python.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from siarrn import alunos, texto
from siarrn.base_local import BaseLocal
from siarrn.cliente_api import AlunoDesconhecido, ErroDeRede
from siarrn.fila_offline import FilaOffline

from .base import ComBanco


class ClienteFalso:
    """Servidor de mentira, que pode ser desligado no meio do teste."""

    def __init__(self, no_ar: bool = True, conhece_alunos: bool = True) -> None:
        self.no_ar_flag = no_ar
        self.conhece_alunos = conhece_alunos
        self.consumos: list[tuple] = []
        self.cadastrados: list[str] = []
        self._proximo_id = 900

    def _exigir_rede(self) -> None:
        if not self.no_ar_flag:
            raise ErroDeRede("servidor fora do ar")

    def cadastrar(self, nome: str, turma: str = "") -> dict:
        self._exigir_rede()
        self._proximo_id += 1
        self.cadastrados.append(nome)
        return {"id": self._proximo_id, "nome": nome, "turma": turma, "codigo": "TESTE123"}

    def registrar_consumo(self, aluno_id: int, registrado_em: str, origem: str = "nome") -> None:
        self._exigir_rede()
        if not self.conhece_alunos:
            raise AlunoDesconhecido(f"o servidor não conhece o aluno {aluno_id}")
        self.consumos.append((aluno_id, registrado_em, origem))

    def baixar_base(self) -> list[dict]:
        self._exigir_rede()
        return [{"id": 1, "nome": "Ana Souza", "turma": "1º A", "codigo": "AAA11111"}]


class ComPastaTemporaria(unittest.TestCase):
    def setUp(self) -> None:
        self._pasta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.pasta = Path(self._pasta.name)

    def tearDown(self) -> None:
        self._pasta.cleanup()


# ---------------------------------------------------------------------------
# Regra de busca
# ---------------------------------------------------------------------------
class RegraDeBusca(unittest.TestCase):
    def test_casa_no_inicio_do_nome(self):
        self.assertTrue(texto.combina("joao silva", "joa"))

    def test_casa_no_inicio_do_sobrenome(self):
        self.assertTrue(texto.combina("joao silva", "sil"))

    def test_nao_casa_no_meio_da_palavra(self):
        """'sil' não pode trazer 'Basílio' — encheria a tela de gente errada."""
        self.assertFalse(texto.combina("basilio nunes", "sil"))

    def test_termo_vazio_nao_casa_com_nada(self):
        self.assertFalse(texto.combina("joao silva", ""))

    def test_normalizacao_remove_acento_e_caixa(self):
        self.assertEqual(texto.normalizar("JÚLIA Conceição"), "julia conceicao")

    def test_normalizacao_colapsa_espacos(self):
        self.assertEqual(texto.normalizar("  Ana   Maria "), "ana maria")


class BuscaBateComOServidor(ComBanco):
    """A busca do totem e a do servidor precisam devolver o mesmo conjunto.

    Enquanto forem duas implementações — uma em SQL, outra em Python — este
    teste é a única coisa que impede as duas de divergirem em silêncio.
    """

    NOMES = [
        ("João Silva", "1º A"),
        ("João Souza", "2º B"),
        ("Júlia Medeiros", "1º A"),
        ("Ana Silveira", "3º A"),
        ("Basílio Nunes", "2º A"),
        ("Maria Conceição", "1º B"),
        ("Ana Maria Lima", "3º B"),
    ]

    TERMOS = ["jo", "joa", "joão", "sil", "SIL", "jul", "júl", "ana", "concei", "med", "zz"]

    def setUp(self) -> None:
        super().setUp()
        # Nome próprio, não `_pasta`: esse atributo é da classe ComBanco e guarda
        # a pasta do SQLite temporário. Sobrescrevê-lo deixa o banco sem
        # referência viva e o arquivo some no meio do teste.
        self._pasta_do_totem = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        registros = [alunos.criar(nome, turma) for nome, turma in self.NOMES]

        self.base = BaseLocal(Path(self._pasta_do_totem.name))
        for registro in registros:
            self.base.acrescentar(registro)

    def tearDown(self) -> None:
        self._pasta_do_totem.cleanup()
        super().tearDown()

    def test_mesmo_resultado_para_todos_os_termos(self):
        for termo in self.TERMOS:
            do_servidor = {a["nome"] for a in alunos.buscar(termo)}
            do_totem = {a["nome"] for a in self.base.buscar(termo)}
            self.assertEqual(
                do_servidor, do_totem,
                f"servidor e totem discordam sobre o termo {termo!r}",
            )


# ---------------------------------------------------------------------------
# Cadastros parecidos
# ---------------------------------------------------------------------------
class CadastrosParecidos(unittest.TestCase):
    @staticmethod
    def _nomes(*nomes):
        return [{"id": i, "nome": n} for i, n in enumerate(nomes)]

    def _pares(self, *nomes):
        return [(a["nome"], b["nome"]) for a, b in texto.pares_suspeitos(self._nomes(*nomes))]

    def test_erro_de_digitacao(self):
        self.assertEqual(self._pares("João Pedro", "Jao Pedro", "Ana Lima"),
                         [("João Pedro", "Jao Pedro")])

    def test_nome_abreviado(self):
        self.assertEqual(self._pares("Maria Silva", "Maria S"), [("Maria Silva", "Maria S")])

    def test_erro_de_digitacao_sem_o_ultimo_sobrenome(self):
        """O caso mais comum na fila, e o primeiro que a tela real deixou passar."""
        self.assertEqual(self._pares("Jao Pedro", "Joao Pedro Lima"),
                         [("Jao Pedro", "Joao Pedro Lima")])

    def test_abreviacao_exige_o_primeiro_nome_inteiro(self):
        self.assertEqual(self._pares("Maria S", "Mariana Silva Pereira"), [])

    def test_nao_junta_nomes_diferentes(self):
        self.assertEqual(self._pares("Ana Lima", "Ana Luiza", "Pedro Alves", "Paulo Alves"), [])

    def test_primeiro_nome_sozinho_nao_casa_com_todo_mundo(self):
        self.assertEqual(self._pares("Maria", "Maria Silva", "Maria Eduarda Costa"), [])

    def test_mais_parecidos_primeiro(self):
        pares = self._pares("Joao Pedro", "Joao Pedro Lima", "Jao Pedro")
        self.assertEqual(pares[0], ("Joao Pedro", "Joao Pedro Lima"))

    def test_quinhentos_alunos_cabem_num_instante(self):
        import random
        import time

        from siarrn import seed
        nomes = seed._nomes_unicos(random.Random(1), 500)
        inicio = time.perf_counter()
        texto.pares_suspeitos(self._nomes(*nomes))
        self.assertLess(time.perf_counter() - inicio, 2.0)


# ---------------------------------------------------------------------------
# Base local
# ---------------------------------------------------------------------------
class BaseLocalTest(ComPastaTemporaria):
    def setUp(self) -> None:
        super().setUp()
        self.base = BaseLocal(self.pasta)

    def test_comeca_vazia(self):
        self.assertTrue(self.base.vazia())
        self.assertEqual(self.base.buscar("joao"), [])

    def test_acrescentar_e_buscar(self):
        self.base.acrescentar({"id": 1, "nome": "João Silva", "turma": "1º A"})
        self.assertEqual(self.base.buscar("joao")[0]["nome"], "João Silva")

    def test_calcula_nome_busca_quando_falta(self):
        """Aluno cadastrado no próprio totem vem sem o campo normalizado."""
        self.base.acrescentar({"id": 1, "nome": "Júlia Gomes", "turma": ""})
        self.assertEqual(self.base.buscar("jul")[0]["nome"], "Júlia Gomes")

    def test_termo_curto_devolve_vazio(self):
        self.base.acrescentar({"id": 1, "nome": "João Silva"})
        self.assertEqual(self.base.buscar("j"), [])

    def test_sobrevive_ao_reinicio(self):
        """O totem é desligado todo dia; a lista precisa estar lá na volta."""
        self.base.acrescentar({"id": 7, "nome": "Ana Souza", "turma": "1º A"})

        outra = BaseLocal(self.pasta)
        self.assertEqual(outra.tamanho(), 1)
        self.assertEqual(outra.buscar("ana")[0]["id"], 7)

    def test_arquivo_corrompido_nao_impede_o_totem_de_abrir(self):
        """Melhor abrir com a lista vazia do que não abrir com a fila esperando."""
        (self.pasta / "alunos.json").write_text("{lixo", encoding="utf-8")
        base = BaseLocal(self.pasta)
        self.assertTrue(base.vazia())

    def test_servidor_fora_preserva_a_copia_anterior(self):
        """Sem rede, a lista de ontem continua valendo — a fila precisa andar."""
        self.base.acrescentar({"id": 1, "nome": "Ana Souza"})
        atualizou = self.base.atualizar(ClienteFalso(no_ar=False))

        self.assertFalse(atualizou)
        self.assertEqual(self.base.tamanho(), 1)

    def test_cartao_de_cadastro_mesclado_ainda_passa(self):
        self.base.acrescentar({"id": 7, "nome": "Joao Pedro", "codigo": "NOVO2345",
                               "codigos_antigos": "VELHO234,OUTRO567"})
        self.assertEqual(self.base.por_codigo("velho234")["id"], 7)
        self.assertEqual(self.base.por_codigo("OUTRO567")["id"], 7)
        self.assertIsNone(self.base.por_codigo("NADA2345"))

    def test_atualizar_substitui_a_lista(self):
        self.base.acrescentar({"id": 99, "nome": "Antigo Registro"})
        self.assertTrue(self.base.atualizar(ClienteFalso()))
        self.assertEqual(self.base.tamanho(), 1)
        self.assertEqual(self.base.buscar("ana")[0]["nome"], "Ana Souza")


# ---------------------------------------------------------------------------
# Fila offline
# ---------------------------------------------------------------------------
class FilaOfflineTest(ComPastaTemporaria):
    def setUp(self) -> None:
        super().setUp()
        self.fila = FilaOffline(self.pasta)
        self.base = BaseLocal(self.pasta)
        self.aluno = {"id": 42, "nome": "Ana Souza", "turma": "1º A"}

    def test_registrar_nao_depende_de_rede(self):
        """O registro é local. Nenhum cliente é consultado aqui."""
        self.fila.registrar(self.aluno)
        self.assertEqual(self.fila.pendentes(), 1)

    def test_sincroniza_e_esvazia(self):
        self.fila.registrar(self.aluno)
        cliente = ClienteFalso()

        self.assertEqual(self.fila.sincronizar(cliente, self.base), 1)
        self.assertEqual(self.fila.pendentes(), 0)
        self.assertEqual(cliente.consumos[0][0], 42)

    def test_servidor_fora_preserva_a_fila(self):
        """O erro que não se pode cometer é apagar da fila o que nunca chegou."""
        self.fila.registrar(self.aluno)

        self.assertEqual(self.fila.sincronizar(ClienteFalso(no_ar=False), self.base), 0)
        self.assertEqual(self.fila.pendentes(), 1)

    def test_fila_sobrevive_ao_reinicio_do_totem(self):
        self.fila.registrar(self.aluno)
        outra = FilaOffline(self.pasta)
        self.assertEqual(outra.pendentes(), 1)

    def test_entrega_tudo_quando_o_servidor_volta(self):
        for _ in range(5):
            self.fila.registrar(self.aluno)

        cliente = ClienteFalso(no_ar=False)
        self.fila.sincronizar(cliente, self.base)
        self.assertEqual(self.fila.pendentes(), 5)

        cliente.no_ar_flag = True
        self.assertEqual(self.fila.sincronizar(cliente, self.base), 5)
        self.assertEqual(self.fila.pendentes(), 0)

    def test_preserva_o_horario_da_fila(self):
        """Almoço registrado offline às 11h47 continua sendo das 11h47."""
        self.fila.registrar(self.aluno)
        cliente = ClienteFalso()
        self.fila.sincronizar(cliente, self.base)

        _, registrado_em, origem = cliente.consumos[0]
        self.assertRegex(registrado_em, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        self.assertEqual(origem, "nome")

    def test_linha_corrompida_nao_trava_as_outras(self):
        """Queda de energia pode truncar a última linha. As demais têm que subir."""
        self.fila.registrar(self.aluno)
        with open(self.pasta / "fila.jsonl", "a", encoding="utf-8") as arquivo:
            arquivo.write('{"aluno_id": 9, "registra\n')
        self.fila.registrar(self.aluno)

        cliente = ClienteFalso()
        self.assertEqual(self.fila.sincronizar(cliente, self.base), 2)

    def test_cadastro_pendente_vira_aluno_de_verdade(self):
        """Quem se cadastrou com a rede caída não pode ficar sem almoçar.

        Na sincronização o aluno é criado no servidor e o almoço registrado —
        os dois de uma vez.
        """
        self.fila.registrar_cadastro_pendente("Novato Recente", "1º C")
        cliente = ClienteFalso()

        self.assertEqual(self.fila.sincronizar(cliente, self.base), 1)
        self.assertEqual(cliente.cadastrados, ["Novato Recente"])
        self.assertEqual(self.fila.pendentes(), 0)
        # E o aluno passa a existir na busca local, sem precisar rebaixar a base.
        self.assertEqual(self.base.buscar("novato")[0]["nome"], "Novato Recente")

    def test_aluno_que_o_servidor_nao_conhece_sai_da_fila(self):
        """Reenviar não resolve, e guardar para sempre entope a fila.

        Este caso apareceu de verdade: o servidor respondia 404 e o cliente
        tratava como sucesso, então o almoço sumia sem deixar rastro. Agora ele
        sai da fila, mas o registro guarda o que aconteceu.
        """
        self.fila.registrar(self.aluno)
        cliente = ClienteFalso(conhece_alunos=False)

        self.assertEqual(self.fila.sincronizar(cliente, self.base), 0)
        self.assertEqual(cliente.consumos, [])
        # Não fica preso: a fila esvazia para não atrasar os dias seguintes.
        self.assertEqual(self.fila.pendentes(), 0)

    def test_servidor_fora_do_ar_e_diferente_de_aluno_desconhecido(self):
        """Um é transitório e volta; o outro não adianta insistir."""
        self.fila.registrar(self.aluno)

        self.fila.sincronizar(ClienteFalso(no_ar=False), self.base)
        self.assertEqual(self.fila.pendentes(), 1, "queda de rede não pode descartar")

        cliente = ClienteFalso()
        self.assertEqual(self.fila.sincronizar(cliente, self.base), 1)

    def test_cadastro_pendente_espera_o_servidor_voltar(self):
        self.fila.registrar_cadastro_pendente("Novato Recente", "1º C")

        self.assertEqual(self.fila.sincronizar(ClienteFalso(no_ar=False), self.base), 0)
        self.assertEqual(self.fila.pendentes(), 1)


class ContaDaSobra(unittest.TestCase):
    """A regra que traduz preparado × servido na frase que a cozinha lê.

    É lógica de negócio, não formatação: define o que conta como sobra
    aceitável e o que merece sinal de atenção no dia seguinte. Roda sem abrir
    janela porque o método é estático.
    """

    @staticmethod
    def _sobra(preparado, consumidos):
        from siarrn.ui_gestao import TelaGestao
        return TelaGestao._texto_da_sobra(preparado, consumidos)

    def test_sem_preparado_informado_pede_o_numero(self):
        texto, _ = self._sobra(None, 74)
        self.assertIn("informe", texto.lower())

    def test_sobra_grande_recebe_cor_de_atencao(self):
        from siarrn import ui_tema as tema
        texto, cor = self._sobra(100, 74)
        self.assertIn("sobraram 26", texto)
        self.assertEqual(cor, tema.COR_AVISO)

    def test_sobra_pequena_esta_ok(self):
        from siarrn import ui_tema as tema
        texto, cor = self._sobra(78, 74)
        self.assertIn("sobraram 4", texto)
        self.assertEqual(cor, tema.COR_SUCESSO)

    def test_margem_minima_nao_vira_alarme(self):
        """Numa escola pequena, três pratos de margem é prudência, não desperdício."""
        from siarrn import ui_tema as tema
        _, cor = self._sobra(23, 20)
        self.assertEqual(cor, tema.COR_SUCESSO)

    def test_acertar_na_mosca(self):
        from siarrn import ui_tema as tema
        texto, cor = self._sobra(74, 74)
        self.assertIn("não sobrou nada", texto)
        self.assertEqual(cor, tema.COR_SUCESSO)

    def test_faltar_comida_e_sinalizado(self):
        """Aluno sem almoço é pior que comida no lixo, e também pede correção."""
        from siarrn import ui_tema as tema
        texto, cor = self._sobra(70, 74)
        self.assertIn("faltaram 4", texto)
        self.assertEqual(cor, tema.COR_AVISO)

    def test_singular_quando_falta_um(self):
        texto, _ = self._sobra(73, 74)
        self.assertIn("faltaram 1 prato", texto)
        self.assertNotIn("pratos", texto)


if __name__ == "__main__":
    unittest.main()
