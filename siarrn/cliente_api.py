"""
SIARRN — Cliente HTTP do totem

Conversa com o servidor. Duas decisões governam este módulo, e as duas vieram
de medição, não de suposição.

**Tempo limite curto.** Um totem que espera dez segundos por uma resposta trava
a fila do almoço, e fila travada faz a cozinha desistir do sistema no primeiro
dia. Nada aqui passa de dois segundos: se a rede não responder nesse prazo,
quem chamou trata como offline e segue em frente.

**Conexão reaproveitada.** Usa `http.client` em vez de `urllib` justamente por
isso — o `urllib` abre uma conexão TCP nova a cada chamada, e a sincronização
manda um almoço por vez. Foi essa a diferença entre trinta segundos e um para
esvaziar uma fila de cem registros, quando o servidor passou a falar HTTP/1.1.
"""
from __future__ import annotations

import http.client
import json
import threading
from urllib.parse import urlsplit

TEMPO_LIMITE = 2.0

# Baixar a base inteira é mais pesado que uma consulta, e acontece fora da fila.
TEMPO_LIMITE_BASE = 15.0


class ErroDeRede(Exception):
    """Falha ao falar com o servidor. Sempre recuperável: o totem segue offline."""


class ClienteApi:
    def __init__(self, config) -> None:
        self._config = config
        self._conexao: http.client.HTTPConnection | None = None
        self._endereco_da_conexao = ""
        # A sincronização roda numa thread de fundo enquanto a interface também
        # pode chamar (num cadastro, por exemplo). Uma conexão HTTP não aguenta
        # duas requisições ao mesmo tempo.
        self._trava = threading.Lock()

    # -----------------------------------------------------------------------
    # Conexão
    # -----------------------------------------------------------------------
    def _abrir(self, tempo_limite: float) -> http.client.HTTPConnection:
        partes = urlsplit(self._config.servidor)
        host = partes.hostname or "localhost"
        porta = partes.port or (443 if partes.scheme == "https" else 80)

        if partes.scheme == "https":
            return http.client.HTTPSConnection(host, porta, timeout=tempo_limite)
        return http.client.HTTPConnection(host, porta, timeout=tempo_limite)

    def _fechar(self) -> None:
        if self._conexao is not None:
            try:
                self._conexao.close()
            except OSError:
                pass
            self._conexao = None

    def _cabecalhos(self) -> dict:
        cabecalhos = {"Content-Type": "application/json", "Accept": "application/json"}
        token = self._config.token
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        return cabecalhos

    def _requisitar(
        self,
        metodo: str,
        caminho: str,
        corpo: dict | None = None,
        tempo_limite: float = TEMPO_LIMITE,
    ):
        """Faz a requisição e devolve o JSON, ou None em 404.

        Tenta duas vezes de propósito. A conexão fica aberta entre chamadas, e
        uma conexão guardada pode ter morrido do outro lado sem aviso — servidor
        reiniciado, rede que oscilou. A primeira tentativa descobre isso; a
        segunda reconecta. Sem essa repetição, todo reinício do servidor
        derrubaria a próxima operação do totem.
        """
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None

        with self._trava:
            for tentativa in (1, 2):
                try:
                    if self._conexao is None or self._endereco_da_conexao != self._config.servidor:
                        self._fechar()
                        self._conexao = self._abrir(tempo_limite)
                        self._endereco_da_conexao = self._config.servidor

                    self._conexao.request(metodo, caminho, body=dados, headers=self._cabecalhos())
                    resposta = self._conexao.getresponse()
                    conteudo = resposta.read()

                    if resposta.status == 404:
                        return None
                    if resposta.status >= 400:
                        raise ErroDeRede(f"servidor respondeu {resposta.status}")
                    if not conteudo:
                        return None
                    return json.loads(conteudo.decode("utf-8"))

                except (http.client.HTTPException, OSError) as erro:
                    self._fechar()
                    if tentativa == 2:
                        raise ErroDeRede(str(erro) or type(erro).__name__) from erro
                except ValueError as erro:
                    self._fechar()
                    raise ErroDeRede("resposta inesperada do servidor") from erro

        raise ErroDeRede("falha desconhecida")

    # -----------------------------------------------------------------------
    # Rotas
    # -----------------------------------------------------------------------
    def no_ar(self) -> bool:
        """Diz se o servidor responde. Nunca levanta: a resposta é o booleano."""
        try:
            return self._requisitar("GET", "/api/ping") is not None
        except ErroDeRede:
            return False

    def baixar_base(self) -> list[dict]:
        """Baixa a lista completa de alunos.

        O totem guarda essa lista em disco e faz toda a busca em memória. É o
        que permite a fila continuar andando com a rede caída.
        """
        alunos = self._requisitar("GET", "/api/alunos/todos", tempo_limite=TEMPO_LIMITE_BASE)
        if not alunos:
            raise ErroDeRede("base de alunos indisponível")
        return alunos

    def cadastrar(self, nome: str, turma: str = "") -> dict:
        resposta = self._requisitar("POST", "/api/alunos", {"nome": nome, "turma": turma})
        if not resposta:
            raise ErroDeRede("cadastro não confirmado")
        return resposta

    def registrar_consumo(self, aluno_id: int, registrado_em: str, origem: str = "nome") -> None:
        """Registra que o aluno almoçou.

        O horário é o do momento em que a pessoa passou pelo totem, não o do
        envio: um almoço registrado offline às 11h47 e sincronizado às 12h30
        continua sendo das 11h47.
        """
        self._requisitar("POST", "/api/consumo", {
            "aluno_id": aluno_id,
            "registrado_em": registrado_em,
            "origem": origem,
        })

    def definir_cardapio(self, cardapio: str) -> None:
        """O que vai ser servido hoje. Só a cozinha sabe."""
        self._requisitar("POST", "/api/refeicao/cardapio", {"cardapio": cardapio})

    def definir_preparado(self, quantidade: int) -> None:
        """Quantos pratos foram preparados — a outra metade da conta da sobra."""
        self._requisitar("POST", "/api/refeicao/preparado", {"preparado": quantidade})

    def painel_de_hoje(self) -> dict:
        painel = self._requisitar("GET", "/api/cozinha/hoje")
        if not painel:
            raise ErroDeRede("painel indisponível")
        return painel

    def fechar(self) -> None:
        with self._trava:
            self._fechar()
