"""
SIARRN — Servidor HTTP/JSON

Implementado 100% com a biblioteca padrão (http.server + json), como o
`api.py` do SIGBEF. Não existe interface web aqui: as rotas devolvem JSON
para o totem (JavaFX) e o app do aluno (Android), e só. A única exceção é
`/siarrn.apk`, que entrega o instalador do app pela rede da escola.

Autenticação
------------
Desligada por padrão. Definindo a variável de ambiente `SIARRN_TOKEN`, todas
as rotas passam a exigir `Authorization: Bearer <token>`. Não é proteção
contra um atacante determinado — é para que um aluno curioso na mesma rede
não consiga inflar a contagem de almoços por diversão, já que essa contagem é
o produto inteiro do sistema.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import alunos, dados, log, previsao, refeicoes

PORTA_PADRAO = 8770

# Locais onde o APK pode estar, na ordem em que são procurados.
_CAMINHOS_APK = (
    Path(dados.BASE_DIR) / "dist" / "siarrn.apk",
    Path(dados.BASE_DIR) / "app-aluno" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk",
    Path(dados.BASE_DIR) / "app-aluno" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
)


def token_configurado() -> str:
    return (os.environ.get("SIARRN_TOKEN") or "").strip()


def ip_local() -> str | None:
    """IP desta máquina na rede da escola, ou None se não houver rede.

    Abre um socket UDP e pergunta ao sistema qual interface seria usada para
    falar com um endereço da própria LAN. Nada é enviado e não depende de
    internet — é só uma consulta à tabela de rotas.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.168.255.255", 1))
        ip = sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()

    if not ip or ip.startswith("127."):
        return None
    return ip


def _apk_disponivel() -> Path | None:
    for caminho in _CAMINHOS_APK:
        if caminho.is_file():
            return caminho
    return None


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "SIARRN"

    # O padrão do BaseHTTPRequestHandler é HTTP/1.0, que fecha a conexão TCP a
    # cada requisição. O totem sincroniza a fila offline um almoço por vez, e
    # com uma conexão nova por item cem registros levavam mais de trinta
    # segundos. Com keep-alive isso cai para menos de um. Exige Content-Length
    # correto em toda resposta — o que `_responder` e `_servir_apk` já fazem.
    protocol_version = "HTTP/1.1"

    # -- infraestrutura ----------------------------------------------------
    def log_message(self, formato: str, *args) -> None:  # noqa: A002
        """Registra a requisição — e nunca deixa o registro derrubar o servidor.

        Aqui havia um `print` direto. Quando a saída padrão ficava indisponível
        (executável sem console, redirecionamento fechado), ele levantava
        exceção, a thread que atendia a requisição morria, e a conexão fechava
        sem resposta: o servidor continuava escutando na porta sem responder
        nada. `log.info` engole qualquer falha de escrita justamente por isso.
        """
        log.info(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def _responder(self, status: int, payload) -> None:
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _erro(self, status: int, mensagem: str) -> None:
        self._responder(status, {"erro": mensagem})

    def _corpo_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _autorizado(self) -> bool:
        esperado = token_configurado()
        if not esperado:
            return True
        cabecalho = self.headers.get("Authorization", "")
        recebido = cabecalho[7:].strip() if cabecalho.startswith("Bearer ") else ""
        return hmac.compare_digest(recebido, esperado)

    # -- rotas -------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        caminho = url.path.rstrip("/") or "/"

        if caminho == "/api/ping":
            return self._responder(200, {"servico": "SIARRN", "ok": True})

        if caminho == "/siarrn.apk":
            return self._servir_apk()

        if not self._autorizado():
            return self._erro(401, "Token ausente ou inválido.")

        if caminho == "/api/alunos/busca":
            termo = (parse_qs(url.query).get("q") or [""])[0]
            return self._responder(200, alunos.buscar(termo))

        if caminho == "/api/alunos/todos":
            return self._responder(200, alunos.todos())

        casamento = re.fullmatch(r"/api/alunos/codigo/([^/]+)", caminho)
        if casamento:
            return self._aluno_por_codigo(unquote(casamento.group(1)))

        if caminho == "/api/refeicao/hoje":
            return self._responder(200, refeicoes.garantir())

        if caminho == "/api/cozinha/hoje":
            return self._responder(200, self._painel_do_dia())

        return self._erro(404, "Rota não encontrada.")

    def do_POST(self) -> None:  # noqa: N802
        caminho = urlparse(self.path).path.rstrip("/") or "/"

        # O corpo é lido antes de qualquer decisão. Em HTTP/1.1 a conexão é
        # reaproveitada, e responder sem consumir os bytes enviados deixaria o
        # corpo desta requisição encostado no início da próxima.
        corpo = self._corpo_json()

        if not self._autorizado():
            return self._erro(401, "Token ausente ou inválido.")

        if caminho == "/api/alunos":
            return self._cadastrar_aluno(corpo)
        if caminho == "/api/alunos/renomear":
            return self._renomear_aluno(corpo)
        if caminho == "/api/alunos/mesclar":
            return self._mesclar_alunos(corpo)
        if caminho == "/api/consumo":
            return self._registrar_consumo(corpo)
        if caminho == "/api/declaracao":
            return self._registrar_declaracao(corpo)
        if caminho == "/api/refeicao/cardapio":
            return self._definir_cardapio(corpo)
        if caminho == "/api/refeicao/preparado":
            return self._definir_preparado(corpo)

        return self._erro(404, "Rota não encontrada.")

    # -- implementação das rotas -------------------------------------------
    def _servir_apk(self) -> None:
        caminho = _apk_disponivel()
        if caminho is None:
            return self._erro(404, "O aplicativo ainda não foi compilado.")

        conteudo = caminho.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.android.package-archive")
        self.send_header("Content-Disposition", 'attachment; filename="siarrn.apk"')
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def _aluno_por_codigo(self, codigo: str) -> None:
        aluno = alunos.por_codigo(codigo)
        if aluno is None:
            return self._erro(404, "Código não encontrado.")

        refeicao = refeicoes.garantir()
        aluno = dict(aluno)
        aluno["declarou"] = refeicoes.declaracao_de(aluno["id"], refeicao["id"])
        aluno["ja_consumiu"] = refeicoes.ja_consumiu(aluno["id"], refeicao["id"])
        return self._responder(200, aluno)

    def _cadastrar_aluno(self, corpo: dict) -> None:
        nome = (corpo.get("nome") or "").strip()
        if not nome:
            return self._erro(400, "Informe o nome do aluno.")
        try:
            aluno = alunos.criar(nome, (corpo.get("turma") or "").strip())
        except (ValueError, RuntimeError) as erro:
            return self._erro(400, str(erro))
        return self._responder(201, aluno)

    def _renomear_aluno(self, corpo: dict) -> None:
        aluno_id = corpo.get("aluno_id")
        if not isinstance(aluno_id, int):
            return self._erro(400, "Informe o aluno_id.")
        if alunos.por_id(aluno_id) is None:
            return self._erro(404, "Aluno não encontrado.")
        try:
            alunos.renomear(aluno_id, corpo.get("nome") or "", corpo.get("turma"))
        except ValueError as erro:
            return self._erro(400, str(erro))
        return self._responder(200, alunos.por_id(aluno_id))

    def _mesclar_alunos(self, corpo: dict) -> None:
        manter, descartar = corpo.get("manter_id"), corpo.get("descartar_id")
        if not isinstance(manter, int) or not isinstance(descartar, int):
            return self._erro(400, "Informe manter_id e descartar_id.")
        try:
            alunos.mesclar(manter, descartar)
        except ValueError as erro:
            return self._erro(400, str(erro))
        return self._responder(200, alunos.por_id(manter))

    def _registrar_consumo(self, corpo: dict) -> None:
        """Registra que o aluno almoçou.

        Devolve 200 mesmo quando o consumo já existia. O totem reenvia a fila
        offline sem saber o que o servidor já tem, e tratar repetição como erro
        faria a fila local nunca esvaziar.
        """
        aluno_id = corpo.get("aluno_id")
        if not isinstance(aluno_id, int):
            return self._erro(400, "Informe o aluno_id.")

        aluno_id = alunos.resolver(aluno_id)
        if aluno_id is None:
            return self._erro(404, "Aluno não encontrado.")

        refeicao_id = corpo.get("refeicao_id") or refeicoes.garantir()["id"]
        novo = refeicoes.registrar_consumo(
            aluno_id,
            refeicao_id,
            corpo.get("registrado_em"),
            (corpo.get("origem") or "nome"),
        )
        return self._responder(200, {"registrado": True, "novo": novo})

    def _registrar_declaracao(self, corpo: dict) -> None:
        aluno_id = corpo.get("aluno_id")
        if not isinstance(aluno_id, int):
            return self._erro(400, "Informe o aluno_id.")
        if not isinstance(corpo.get("vai"), bool):
            return self._erro(400, "Informe 'vai' como true ou false.")

        aluno_id = alunos.resolver(aluno_id)
        if aluno_id is None:
            return self._erro(404, "Aluno não encontrado.")

        refeicao_id = corpo.get("refeicao_id") or refeicoes.garantir()["id"]
        refeicoes.declarar(aluno_id, refeicao_id, corpo["vai"])
        return self._responder(200, {"declarado": True, "vai": corpo["vai"]})

    def _definir_cardapio(self, corpo: dict) -> None:
        cardapio = (corpo.get("cardapio") or "").strip()
        refeicao_id = corpo.get("refeicao_id") or refeicoes.garantir()["id"]
        refeicoes.definir_cardapio(refeicao_id, cardapio)
        return self._responder(200, {"refeicao_id": refeicao_id, "cardapio": cardapio})

    def _definir_preparado(self, corpo: dict) -> None:
        """Quantos pratos a cozinha de fato preparou.

        É a outra metade da conta do desperdício. O sistema já sabia quantos
        almoçaram; sem este número, sabia quantos comeram mas não quanto foi
        jogado fora — e reduzir a sobra é o objetivo declarado do projeto.
        """
        quantidade = corpo.get("preparado")
        if not isinstance(quantidade, int) or quantidade < 0:
            return self._erro(400, "Informe 'preparado' como um número inteiro não negativo.")

        refeicao_id = corpo.get("refeicao_id") or refeicoes.garantir()["id"]
        refeicoes.definir_preparado(refeicao_id, quantidade)
        return self._responder(200, {"refeicao_id": refeicao_id, "preparado": quantidade})

    def _painel_do_dia(self) -> dict:
        """Tudo o que a cozinha precisa ver, numa resposta só."""
        refeicao = refeicoes.garantir()
        sim, nao = refeicoes.contagem_declaracoes(refeicao["id"])

        resultado = previsao.calcular(
            sim=sim,
            nao=nao,
            silenciosos=refeicoes.historico_dos_silenciosos(refeicao["id"]),
            taxa_media=refeicoes.taxa_media_escola(refeicao["id"]),
        )

        refeicoes.registrar_previsao(refeicao["id"], resultado["previsto"])
        resultado["consumidos"] = refeicoes.total_consumido(refeicao["id"])
        resultado["refeicao_id"] = refeicao["id"]
        resultado["data"] = refeicao["data"]
        resultado["cardapio"] = refeicao["cardapio"]
        resultado["preparado"] = refeicao["preparado"]
        resultado["total_alunos"] = alunos.contar()
        return resultado


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------
class Servidor(ThreadingHTTPServer):
    """Servidor que devolve a conexão do banco quando o cliente vai embora.

    A conexão SQLite é mantida por thread (ver `dados.get_connection`), e aqui
    cada cliente é atendido na sua. Enquanto ele fica conectado — com
    keep-alive, o totem fica —, a conexão é reaproveitada; quando desconecta, a
    thread acaba e a conexão precisa ser fechada explicitamente. Sem isto ela
    ficaria órfã esperando o coletor de lixo, e num dia de almoço isso vira
    dezenas de conexões abertas à toa.
    """

    daemon_threads = True

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            dados.fechar_conexao()


def criar_servidor(porta: int = PORTA_PADRAO) -> Servidor:
    """Sobe o servidor em todas as interfaces — o totem e os celulares
    precisam alcançá-lo pela rede da escola, não só pelo loopback."""
    dados.init_db()
    return Servidor(("0.0.0.0", porta), Handler)


def endereco_visivel(porta: int) -> str:
    ip = ip_local() or "localhost"
    return f"http://{ip}:{porta}"
