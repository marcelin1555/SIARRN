"""
SIARRN — Camada de banco de dados (SQLite)

Centraliza conexão, criação do esquema e utilitários de acesso. Este módulo
não conhece HTTP nem interface: só guarda e devolve dados.
"""
from __future__ import annotations

import os
import sqlite3
import sys
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
    DB_PATH = Path(caminho).expanduser().resolve()
    DATA_DIR = DB_PATH.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com row_factory configurado.

    `timeout=10` faz escritas concorrentes esperarem em vez de falhar na hora
    com "database is locked" — o totem sincronizando uma fila offline enquanto
    a gestão consulta o painel é justamente esse caso. O modo WAL permite
    leituras durante uma escrita.

    `synchronous = NORMAL` é o que torna o registro de almoços viável em disco
    lento. No padrão (FULL) o SQLite força um fsync a cada commit, e medindo
    aqui isso custava cerca de cinquenta milissegundos por operação — cem
    almoços levavam quase dezesseis segundos para sincronizar. Com WAL, NORMAL
    continua íntegro se o programa cair; o risco fica restrito a perder os
    últimos commits numa queda de energia. É um risco aceitável neste sistema
    justamente porque o totem guarda tudo na fila local e reenvia — e a rota de
    consumo é idempotente, então reenviar não duplica nada.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def db_cursor():
    """Context manager: abre conexão, comita ou faz rollback automaticamente."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
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
