"""
SIARRN — Camada de banco de dados (SQLite)

Centraliza conexão, criação do esquema e utilitários de acesso. Este módulo
não conhece HTTP nem interface: só guarda e devolve dados.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


def _diretorio_padrao() -> Path:
    """Determina onde guardar o banco SQLite.

    Ordem de prioridade:
      1. Variável de ambiente SIARRN_DB_PATH (caminho completo)
      2. Pasta `data/` ao lado do código fonte (modo desenvolvimento)
      3. %APPDATA%/SIARRN (Windows) ou ~/.local/share/SIARRN (Linux)
         quando rodando como executável empacotado.
    """
    rodando_empacotado = getattr(sys, "frozen", False)

    if rodando_empacotado:
        if sys.platform == "win32":
            return Path(os.environ.get("APPDATA", Path.home())) / "SIARRN"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "SIARRN"
        return Path.home() / ".local" / "share" / "SIARRN"

    return BASE_DIR / "data"


_env_db = os.environ.get("SIARRN_DB_PATH")
if _env_db:
    DB_PATH = Path(_env_db).expanduser().resolve()
    DATA_DIR = DB_PATH.parent
else:
    DATA_DIR = _diretorio_padrao()
    DB_PATH = DATA_DIR / "siarrn.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def usar_banco(caminho: str | Path) -> None:
    """Aponta o módulo para outro arquivo de banco.

    Existe para os testes: cada um roda contra um SQLite temporário e descartável,
    sem risco de encostar no banco real da escola.
    """
    global DB_PATH, DATA_DIR  # noqa: PLW0603
    fechar_conexao()
    DB_PATH = Path(caminho).expanduser().resolve()
    DATA_DIR = DB_PATH.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
# A conexão é guardada por thread e reaproveitada. Objetos de conexão SQLite
# não podem ser compartilhados entre threads, e o servidor atende cada cliente
# na sua — então uma por thread é o meio-termo entre segurança e custo.
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Devolve a conexão desta thread, abrindo-a na primeira vez.

    **A conexão fica aberta de propósito, e isso vale mais que qualquer outro
    ajuste deste módulo.** No modo WAL, fechar a última conexão de um banco
    dispara um checkpoint — o SQLite copia o conteúdo do arquivo `-wal` de
    volta para o principal. Abrindo e fechando a cada operação, toda escrita
    pagava esse checkpoint: medido aqui, 165 ms por almoço registrado contra
    0,6 ms reaproveitando a conexão. Duzentas e noventa e sete vezes.

    `timeout=10` faz escritas concorrentes esperarem em vez de falhar na hora
    com "database is locked" — o totem sincronizando a fila offline enquanto a
    cozinha consulta o painel é justamente esse caso.

    `synchronous = NORMAL` dispensa o fsync a cada commit. Com WAL isso continua
    íntegro se o programa cair; o risco fica restrito a perder os últimos
    commits numa queda de energia, e é aceitável aqui porque o totem guarda tudo
    na fila local e reenvia — e a rota de consumo é idempotente.
    """
    conexao = getattr(_local, "conexao", None)
    caminho_aberto = getattr(_local, "caminho", None)

    # Os testes trocam de banco entre um caso e outro; uma conexão apontando
    # para o arquivo anterior precisa ser descartada.
    if conexao is not None and caminho_aberto != str(DB_PATH):
        fechar_conexao()
        conexao = None

    if conexao is None:
        conexao = sqlite3.connect(DB_PATH, timeout=10)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON;")
        conexao.execute("PRAGMA journal_mode = WAL;")
        conexao.execute("PRAGMA synchronous = NORMAL;")
        _local.conexao = conexao
        _local.caminho = str(DB_PATH)

    return conexao


def fechar_conexao() -> None:
    """Fecha a conexão desta thread, se houver."""
    conexao = getattr(_local, "conexao", None)
    if conexao is not None:
        try:
            conexao.close()
        except sqlite3.Error:
            pass
        _local.conexao = None
        _local.caminho = None


@contextmanager
def db_cursor():
    """Context manager: comita ou faz rollback automaticamente.

    Não fecha a conexão ao sair — ver `get_connection` para o porquê.
    """
    conexao = get_connection()
    cur = conexao.cursor()
    try:
        yield cur
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
# Notas de modelagem que valem a leitura antes de mexer aqui:
#
# * `declaracao` e `consumo` usam chave primária composta (aluno_id, refeicao_id).
#   Em `consumo` isso é o que torna o registro idempotente: o totem pode reenviar
#   a mesma fila offline quantas vezes for e ninguém é contado duas vezes.
#
# * `consumo.registrado_em` NÃO tem valor padrão de propósito. O horário vem do
#   totem, que pode ter registrado offline às 11h47 e sincronizado às 12h30 —
#   guardar o momento da escrita no servidor apagaria a hora real da fila.
#
# * `aluno.mesclado_em` aponta para o cadastro que absorveu este, quando o mesmo
#   aluno se cadastrou duas vezes. O registro antigo fica inativo em vez de ser
#   apagado: o cartão impresso dele, o celular e a fila offline de algum totem
#   ainda podem trazer o id ou o código antigo, e apagar faria esses almoços
#   serem descartados.
#
# * `refeicao` tem UNIQUE(data, turno) porque hoje só existe almoço, mas o
#   campo `turno` já deixa a porta aberta pra lanche sem exigir migração.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS aluno (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    nome_busca TEXT NOT NULL,
    turma TEXT NOT NULL DEFAULT '',
    codigo TEXT UNIQUE NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    mesclado_em INTEGER REFERENCES aluno(id)
);

CREATE INDEX IF NOT EXISTS idx_aluno_nome_busca ON aluno(nome_busca);

CREATE TABLE IF NOT EXISTS refeicao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    turno TEXT NOT NULL DEFAULT 'almoco',
    cardapio TEXT,
    previsto INTEGER,
    preparado INTEGER,
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (data, turno)
);

CREATE TABLE IF NOT EXISTS declaracao (
    aluno_id INTEGER NOT NULL REFERENCES aluno(id) ON DELETE CASCADE,
    refeicao_id INTEGER NOT NULL REFERENCES refeicao(id) ON DELETE CASCADE,
    vai INTEGER NOT NULL,
    declarado_em TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (aluno_id, refeicao_id)
);

CREATE TABLE IF NOT EXISTS consumo (
    aluno_id INTEGER NOT NULL REFERENCES aluno(id) ON DELETE CASCADE,
    refeicao_id INTEGER NOT NULL REFERENCES refeicao(id) ON DELETE CASCADE,
    registrado_em TEXT NOT NULL,
    origem TEXT NOT NULL DEFAULT 'nome',
    PRIMARY KEY (aluno_id, refeicao_id)
);

CREATE INDEX IF NOT EXISTS idx_consumo_refeicao ON consumo(refeicao_id);
CREATE INDEX IF NOT EXISTS idx_declaracao_refeicao ON declaracao(refeicao_id);
"""


def init_db() -> None:
    """Cria o esquema se ainda não existir. Seguro de chamar toda inicialização."""
    with db_cursor() as cur:
        cur.executescript(SCHEMA_SQL)
        # Bancos criados antes da coluna existir. O CREATE TABLE acima não
        # altera tabela que já existe.
        colunas = {linha[1] for linha in cur.execute("PRAGMA table_info(aluno)")}
        if "mesclado_em" not in colunas:
            cur.execute("ALTER TABLE aluno ADD COLUMN mesclado_em INTEGER REFERENCES aluno(id)")


# ---------------------------------------------------------------------------
# Utilitários de consulta
# ---------------------------------------------------------------------------
def buscar_um(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Executa a consulta e devolve a primeira linha, ou None."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def buscar_todos(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Executa a consulta e devolve todas as linhas."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def executar(sql: str, params: tuple = ()) -> int:
    """Executa um comando de escrita e devolve o lastrowid."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid
