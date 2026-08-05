"""
SIARRN — Cadastro e busca de alunos

O aluno se cadastra sozinho, na primeira vez que usa o totem. Não existe
carteirinha na escola e ninguém decora matrícula, então a identificação é
pelo nome — que ninguém esquece — e o código gerado aqui vira o QR.
"""
from __future__ import annotations

import secrets
import sqlite3
import unicodedata

from . import dados

# Alfabeto sem caracteres ambíguos. Se alguém precisar ler o código impresso
# e digitar à mão, 0/O e 1/I/L viram fonte de erro — melhor nem existirem.
_ALFABETO_CODIGO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_TAMANHO_CODIGO = 8

# Quantos nomes o totem mostra de uma vez. Lista longa numa fila é pior que
# lista curta: o aluno lê tudo em vez de achar o dele.
LIMITE_BUSCA = 20


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Reduz o nome à forma usada na busca: minúsculo, sem acento, sem espaço extra.

    É o que faz "joao", "João" e "JOAO" encontrarem a mesma pessoa. Numa fila
    de almoço ninguém vai acertar o acento — e não deveria precisar.
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def gerar_codigo() -> str:
    """Gera um código aleatório para o QR do aluno.

    Aleatório em vez de sequencial não é segurança — ninguém ganha nada se
    passando por outro, já que todos têm direito ao almoço. É só para que
    ninguém consiga gerar o cartão do colega por brincadeira.
    """
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_TAMANHO_CODIGO))


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------
def criar(nome: str, turma: str = "") -> dict:
    """Cadastra um aluno e devolve o registro criado, já com o código.

    Repete a geração do código em caso de colisão. Com 31^8 combinações isso
    é praticamente impossível, mas a alternativa é um cadastro que falha na
    frente da fila — e aí a probabilidade deixa de ser argumento.
    """
    nome = " ".join(nome.split())
    if not nome:
        raise ValueError("O nome não pode ser vazio.")

    turma = " ".join(turma.split())
    nome_busca = normalizar(nome)

    for _ in range(10):
        codigo = gerar_codigo()
        try:
            aluno_id = dados.executar(
                "INSERT INTO aluno (nome, nome_busca, turma, codigo) VALUES (?, ?, ?, ?)",
                (nome, nome_busca, turma, codigo),
            )
        except sqlite3.IntegrityError:
            continue  # código repetido: sorteia outro
        return {
            "id": aluno_id,
            "nome": nome,
            "turma": turma,
            "codigo": codigo,
        }

    raise RuntimeError("Não foi possível gerar um código único para o aluno.")


def renomear(aluno_id: int, nome: str, turma: str | None = None) -> None:
    """Corrige nome (e opcionalmente turma) de um aluno, usado no modo gestão.

    Existe porque cadastro feito às pressas na fila gera "Jõao" e "maria s".
    """
    nome = " ".join(nome.split())
    if not nome:
        raise ValueError("O nome não pode ser vazio.")

    if turma is None:
        dados.executar(
            "UPDATE aluno SET nome = ?, nome_busca = ? WHERE id = ?",
            (nome, normalizar(nome), aluno_id),
        )
    else:
        dados.executar(
            "UPDATE aluno SET nome = ?, nome_busca = ?, turma = ? WHERE id = ?",
            (nome, normalizar(nome), " ".join(turma.split()), aluno_id),
        )


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def _como_dict(linha: sqlite3.Row | None) -> dict | None:
    return dict(linha) if linha is not None else None


def por_id(aluno_id: int) -> dict | None:
    return _como_dict(
        dados.buscar_um(
            "SELECT id, nome, turma, codigo FROM aluno WHERE id = ? AND ativo = 1",
            (aluno_id,),
        )
    )


def por_codigo(codigo: str) -> dict | None:
    """Encontra o aluno pelo código do QR. Aceita o código em qualquer caixa."""
    return _como_dict(
        dados.buscar_um(
            "SELECT id, nome, turma, codigo FROM aluno WHERE codigo = ? AND ativo = 1",
            (codigo.strip().upper(),),
        )
    )


def buscar(termo: str, limite: int = LIMITE_BUSCA) -> list[dict]:
    """Busca alunos por início de qualquer parte do nome.

    "sil" encontra "João Silva" e "Ana Silveira", mas não "Basilio" — casar no
    meio da palavra encheria a tela de gente errada. O aluno da fila digita o
    começo do primeiro nome ou do sobrenome, e é isso que precisa funcionar.
    """
    termo = normalizar(termo)
    if len(termo) < 2:
        return []

    linhas = dados.buscar_todos(
        """
        SELECT id, nome, turma, codigo
          FROM aluno
         WHERE ativo = 1
           AND (nome_busca LIKE ? OR nome_busca LIKE ?)
         ORDER BY nome
         LIMIT ?
        """,
        (f"{termo}%", f"% {termo}%", limite),
    )
    return [dict(linha) for linha in linhas]


def todos() -> list[dict]:
    """Base completa — usada pelo totem no início do dia e pela impressão de cartões.

    O totem precisa dessa lista em disco para continuar respondendo se a rede cair.
    """
    linhas = dados.buscar_todos(
        "SELECT id, nome, nome_busca, turma, codigo FROM aluno WHERE ativo = 1 ORDER BY nome"
    )
    return [dict(linha) for linha in linhas]


def contar() -> int:
    linha = dados.buscar_um("SELECT COUNT(*) AS total FROM aluno WHERE ativo = 1")
    return linha["total"] if linha else 0
