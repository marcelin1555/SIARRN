"""
Testes da API, com o servidor no ar de verdade.

Sobe um `ThreadingHTTPServer` numa porta livre e conversa com ele por HTTP.
Testar contra o servidor real (em vez de chamar as funções direto) é o que pega
erro de rota, de código de status e de formato — exatamente o que o totem e o
app vão encontrar.
"""
from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from siarrn import alunos, api, refeicoes

from .base import ComBanco


class _HandlerSilencioso(api.Handler):
    """Mesmo handler, sem imprimir cada requisição na saída dos testes."""

    def log_message(self, formato: str, *args) -> None:  # noqa: A002
        pass


class ServidorNoAr(ComBanco):
    def setUp(self) -> None:
        super().setUp()
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), _HandlerSilencioso)
        self.porta = self.servidor.server_address[1]
        self.thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    # -- utilitários -------------------------------------------------------
    def _url(self, caminho: str) -> str:
        return f"http://127.0.0.1:{self.porta}{caminho}"

    def _requisitar(self, caminho: str, payload=None, metodo=None, token=None):
        """Devolve (status, corpo). Não levanta em erro HTTP — o status é o teste."""
        dados_envio = json.dumps(payload).encode("utf-8") if payload is not None else None
        pedido = urllib.request.Request(self._url(caminho), data=dados_envio, method=metodo)
        pedido.add_header("Content-Type", "application/json")
        if token:
            pedido.add_header("Authorization", f"Bearer {token}")

        try:
            with urllib.request.urlopen(pedido, timeout=5) as resposta:
                return resposta.status, json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            corpo = erro.read().decode("utf-8")
            return erro.code, json.loads(corpo) if corpo else {}

    def _get(self, caminho: str, token=None):
        return self._requisitar(caminho, token=token)

    def _post(self, caminho: str, payload: dict, token=None):
        return self._requisitar(caminho, payload=payload, token=token)


class Rotas(ServidorNoAr):
    def test_ping(self):
        status, corpo = self._get("/api/ping")
        self.assertEqual(status, 200)
        self.assertTrue(corpo["ok"])

    def test_rota_desconhecida_devolve_404(self):
        self.assertEqual(self._get("/api/inexistente")[0], 404)

    def test_refeicao_de_hoje_e_criada_sob_demanda(self):
        status, corpo = self._get("/api/refeicao/hoje")
        self.assertEqual(status, 200)
        self.assertIn("id", corpo)
        self.assertEqual(corpo["turno"], "almoco")


class Alunos(ServidorNoAr):
    def test_cadastro_devolve_201_e_codigo(self):
        status, corpo = self._post("/api/alunos", {"nome": "Maria Silva", "turma": "2º A"})
        self.assertEqual(status, 201)
        self.assertEqual(len(corpo["codigo"]), 8)

    def test_cadastro_sem_nome_devolve_400(self):
        self.assertEqual(self._post("/api/alunos", {"turma": "2º A"})[0], 400)

    def test_busca_encontra_o_cadastrado(self):
        self._post("/api/alunos", {"nome": "João Pereira", "turma": "1º A"})
        status, corpo = self._get("/api/alunos/busca?q=joao")
        self.assertEqual(status, 200)
        self.assertEqual(corpo[0]["nome"], "João Pereira")

    def test_busca_aceita_acento_na_consulta(self):
        self._post("/api/alunos", {"nome": "Júlia Gomes"})
        status, corpo = self._get("/api/alunos/busca?q=J%C3%9ALIA")
        self.assertEqual(status, 200)
        self.assertEqual(len(corpo), 1)

    def test_consulta_por_codigo_traz_situacao_do_dia(self):
        _, aluno = self._post("/api/alunos", {"nome": "Pedro Lima"})
        status, corpo = self._get(f"/api/alunos/codigo/{aluno['codigo']}")

        self.assertEqual(status, 200)
        self.assertIsNone(corpo["declarou"])
        self.assertFalse(corpo["ja_consumiu"])

    def test_codigo_inexistente_devolve_404(self):
        self.assertEqual(self._get("/api/alunos/codigo/ZZZZZZZZ")[0], 404)


class Consumo(ServidorNoAr):
    def setUp(self) -> None:
        super().setUp()
        _, self.aluno = self._post("/api/alunos", {"nome": "Ana Souza", "turma": "1º A"})

    def test_registro_repetido_responde_200_e_conta_uma_vez(self):
        """O totem reenvia a fila offline sem saber o que o servidor já recebeu.

        Se repetição virasse erro, a fila local nunca esvaziaria — e o totem
        ficaria tentando para sempre.
        """
        primeiro = self._post("/api/consumo", {"aluno_id": self.aluno["id"], "origem": "nome"})
        segundo = self._post("/api/consumo", {"aluno_id": self.aluno["id"], "origem": "nome"})

        self.assertEqual(primeiro, (200, {"registrado": True, "novo": True}))
        self.assertEqual(segundo, (200, {"registrado": True, "novo": False}))

        _, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(painel["consumidos"], 1)

    def test_aluno_inexistente_devolve_404(self):
        self.assertEqual(self._post("/api/consumo", {"aluno_id": 9999})[0], 404)

    def test_sem_aluno_id_devolve_400(self):
        self.assertEqual(self._post("/api/consumo", {"origem": "qr"})[0], 400)

    def test_aceita_horario_do_totem(self):
        status, _ = self._post(
            "/api/consumo",
            {
                "aluno_id": self.aluno["id"],
                "registrado_em": "2026-08-04 11:47:00",
                "origem": "qr",
            },
        )
        self.assertEqual(status, 200)


class Declaracao(ServidorNoAr):
    def setUp(self) -> None:
        super().setUp()
        _, self.aluno = self._post("/api/alunos", {"nome": "Bruno Costa"})

    def test_declarar_presenca_aparece_no_painel(self):
        status, _ = self._post("/api/declaracao", {"aluno_id": self.aluno["id"], "vai": True})
        self.assertEqual(status, 200)

        _, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(painel["sim"], 1)
        self.assertEqual(painel["nao"], 0)

    def test_declarar_ausencia_aparece_no_painel(self):
        self._post("/api/declaracao", {"aluno_id": self.aluno["id"], "vai": False})
        _, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(painel["nao"], 1)

    def test_vai_precisa_ser_booleano(self):
        resposta = self._post("/api/declaracao", {"aluno_id": self.aluno["id"], "vai": "sim"})
        self.assertEqual(resposta[0], 400)


class Painel(ServidorNoAr):
    def test_traz_tudo_que_a_cozinha_precisa(self):
        for nome in ("Ana Lima", "Beto Rocha", "Carla Dias"):
            self._post("/api/alunos", {"nome": nome})

        status, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(status, 200)
        for campo in ("previsto", "sim", "nao", "silenciosos", "consumidos", "confianca"):
            self.assertIn(campo, painel)

    def test_primeiro_dia_conta_todos_e_admite_nao_ter_dados(self):
        """Escola nova no sistema: sem histórico, o painel não finge que sabe."""
        for nome in ("Ana Lima", "Beto Rocha", "Carla Dias"):
            self._post("/api/alunos", {"nome": nome})

        _, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(painel["previsto"], 3)
        self.assertEqual(painel["confianca"], "sem_dados")


class Autenticacao(ServidorNoAr):
    def setUp(self) -> None:
        super().setUp()
        self._token_anterior = os.environ.get("SIARRN_TOKEN")
        os.environ["SIARRN_TOKEN"] = "segredo-da-escola"

    def tearDown(self) -> None:
        if self._token_anterior is None:
            os.environ.pop("SIARRN_TOKEN", None)
        else:
            os.environ["SIARRN_TOKEN"] = self._token_anterior
        super().tearDown()

    def test_sem_token_recusa(self):
        self.assertEqual(self._get("/api/alunos/todos")[0], 401)

    def test_token_errado_recusa(self):
        self.assertEqual(self._get("/api/alunos/todos", token="chute")[0], 401)

    def test_token_correto_permite(self):
        self.assertEqual(self._get("/api/alunos/todos", token="segredo-da-escola")[0], 200)

    def test_ping_continua_aberto(self):
        """O totem precisa conseguir descobrir se o servidor está no ar."""
        self.assertEqual(self._get("/api/ping")[0], 200)


class Integracao(ServidorNoAr):
    def test_ciclo_completo_de_um_dia(self):
        """Cadastro na fila, declaração pelo app, almoço registrado no totem."""
        _, aluno = self._post("/api/alunos", {"nome": "Rafael Dantas", "turma": "3º A"})
        self._post("/api/declaracao", {"aluno_id": aluno["id"], "vai": True})
        self._post("/api/consumo", {"aluno_id": aluno["id"], "origem": "qr"})

        _, painel = self._get("/api/cozinha/hoje")
        self.assertEqual(painel["sim"], 1)
        self.assertEqual(painel["consumidos"], 1)
        self.assertEqual(painel["previsto"], 1)

        _, consulta = self._get(f"/api/alunos/codigo/{aluno['codigo']}")
        self.assertTrue(consulta["declarou"])
        self.assertTrue(consulta["ja_consumiu"])

    def test_previsao_do_dia_fica_registrada(self):
        self._post("/api/alunos", {"nome": "Sofia Melo"})
        _, painel = self._get("/api/cozinha/hoje")

        refeicao = refeicoes.garantir()
        self.assertEqual(refeicao["previsto"], painel["previsto"])
        self.assertEqual(alunos.contar(), 1)


if __name__ == "__main__":
    unittest.main()
