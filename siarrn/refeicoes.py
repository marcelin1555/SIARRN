"""
SIARRN — Refeições, declarações e consumos

Uma refeição é um dia mais um turno. Hoje só existe almoço, mas o turno já
está no modelo para que lanche não exija migração depois.

Duas coisas diferentes moram aqui:

  * **declaração** — o que o aluno disse que ia fazer, antes do almoço.
  * **consumo**    — o que de fato aconteceu, registrado no totem da fila.

A segunda é a que nunca existiu na escola, e é dela que sai todo o valor do
sistema: sem medir quem realmente almoçou, qualquer previsão é chute.
"""
from __future__ import annotations

from datetime import datetime

from . import dados

TURNO_PADRAO = "almoco"

# Quantas refeições passadas entram no cálculo da taxa histórica de cada aluno.
# Vinte cobre cerca de um mês letivo: recente o bastante para refletir o hábito
# atual, longo o bastante para não oscilar por causa de uma semana atípica.
JANELA_HISTORICO = 20


def hoje() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Refeição
# ---------------------------------------------------------------------------
def garantir(data: str | None = None, turno: str = TURNO_PADRAO) -> dict:
    """Devolve a refeição do dia, criando-a se for a primeira chamada.

    Chamado por qualquer caminho que precise da refeição atual — totem, app ou
    gestão. Quem chegar primeiro cria; os demais encontram.
    """
    data = data or hoje()
    consulta = (
        "SELECT id, data, turno, cardapio, previsto, preparado"
        "  FROM refeicao WHERE data = ? AND turno = ?"
    )

    # Consulta antes de inserir. Esta função é chamada em todo registro de
    # almoço, e a refeição do dia já existe desde a primeira pessoa da fila —
    # um INSERT OR IGNORE aqui seria uma escrita (e um commit) inútil no
    # caminho mais quente do sistema.
    existente = dados.buscar_um(consulta, (data, turno))
    if existente is not None:
        return dict(existente)

    with dados.db_cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO refeicao (data, turno) VALUES (?, ?)",
            (data, turno),
        )
        cur.execute(consulta, (data, turno))
        return dict(cur.fetchone())


def definir_cardapio(refeicao_id: int, cardapio: str) -> None:
    """Registra o que vai ser servido.

    Parece detalhe, mas é o campo que em um mês responde "quando tem peixe,
    aparecem 30% menos" — e é assim que a sobra deixa de ser mistério.
    """
    dados.executar(
        "UPDATE refeicao SET cardapio = ? WHERE id = ?", (cardapio.strip(), refeicao_id)
    )


def definir_preparado(refeicao_id: int, quantidade: int) -> None:
    """Quantos pratos a cozinha de fato preparou — o outro lado da conta da sobra."""
    dados.executar(
        "UPDATE refeicao SET preparado = ? WHERE id = ?", (quantidade, refeicao_id)
    )


def registrar_previsao(refeicao_id: int, previsto: int) -> None:
    """Guarda a previsão do dia para depois dar pra comparar com o real.

    Congela no primeiro almoço registrado. O painel recalcula o dia todo, e
    cada aluno que se cadastra na fila soma mais um silencioso à conta: sem o
    congelamento, o número guardado seria o do fim do almoço, inflado por quem
    já comeu, e não o que a cozinha viu ao decidir quanto cozinhar.
    """
    dados.executar(
        """
        UPDATE refeicao SET previsto = ?
         WHERE id = ?
           AND NOT EXISTS (SELECT 1 FROM consumo WHERE refeicao_id = ?)
        """,
        (previsto, refeicao_id, refeicao_id),
    )


# ---------------------------------------------------------------------------
# Declaração
# ---------------------------------------------------------------------------
def declarar(aluno_id: int, refeicao_id: int, vai: bool) -> None:
    """Registra (ou troca) a intenção do aluno. Ele pode mudar de ideia à vontade."""
    dados.executar(
        """
        INSERT INTO declaracao (aluno_id, refeicao_id, vai, declarado_em)
             VALUES (?, ?, ?, ?)
        ON CONFLICT (aluno_id, refeicao_id)
          DO UPDATE SET vai = excluded.vai, declarado_em = excluded.declarado_em
        """,
        (aluno_id, refeicao_id, 1 if vai else 0, agora()),
    )


def declaracao_de(aluno_id: int, refeicao_id: int) -> bool | None:
    """Devolve True (vou), False (não vou) ou None (não declarou nada).

    A distinção entre False e None é o coração do sistema: quem disse que não
    vem sai da conta, quem não disse nada entra pelo histórico.
    """
    linha = dados.buscar_um(
        "SELECT vai FROM declaracao WHERE aluno_id = ? AND refeicao_id = ?",
        (aluno_id, refeicao_id),
    )
    if linha is None:
        return None
    return bool(linha["vai"])


# ---------------------------------------------------------------------------
# Consumo
# ---------------------------------------------------------------------------
def registrar_consumo(
    aluno_id: int,
    refeicao_id: int,
    registrado_em: str | None = None,
    origem: str = "nome",
) -> bool:
    """Registra que o aluno almoçou. Devolve True se foi um registro novo.

    É idempotente de propósito: o totem guarda a fila em disco quando está sem
    rede e reenvia depois, às vezes mais de uma vez. Reenviar o mesmo consumo
    não pode inflar a contagem — a chave primária composta garante isso.

    O `registrado_em` vem do totem, não do servidor. Um almoço registrado
    offline às 11h47 e sincronizado às 12h30 continua sendo das 11h47.
    """
    with dados.db_cursor() as cur:
        cur.execute(
            """
            INSERT OR IGNORE INTO consumo (aluno_id, refeicao_id, registrado_em, origem)
                 VALUES (?, ?, ?, ?)
            """,
            (aluno_id, refeicao_id, registrado_em or agora(), origem),
        )
        return cur.rowcount > 0


def ja_consumiu(aluno_id: int, refeicao_id: int) -> bool:
    linha = dados.buscar_um(
        "SELECT 1 FROM consumo WHERE aluno_id = ? AND refeicao_id = ?",
        (aluno_id, refeicao_id),
    )
    return linha is not None


def total_consumido(refeicao_id: int) -> int:
    linha = dados.buscar_um(
        "SELECT COUNT(*) AS total FROM consumo WHERE refeicao_id = ?", (refeicao_id,)
    )
    return linha["total"] if linha else 0


# ---------------------------------------------------------------------------
# Insumos da previsão
# ---------------------------------------------------------------------------
def contagem_declaracoes(refeicao_id: int) -> tuple[int, int]:
    """Devolve (quantos disseram que vêm, quantos avisaram ausência)."""
    linha = dados.buscar_um(
        """
        SELECT SUM(CASE WHEN vai = 1 THEN 1 ELSE 0 END) AS sim,
               SUM(CASE WHEN vai = 0 THEN 1 ELSE 0 END) AS nao
          FROM declaracao
         WHERE refeicao_id = ?
        """,
        (refeicao_id,),
    )
    if linha is None:
        return 0, 0
    return linha["sim"] or 0, linha["nao"] or 0


def historico_dos_silenciosos(
    refeicao_id: int, janela: int = JANELA_HISTORICO
) -> list[tuple[int, int]]:
    """Para cada aluno que não declarou nada, devolve (consumos, oportunidades).

    "Oportunidades" conta só as refeições posteriores ao cadastro do aluno.
    Sem isso, quem entrou na semana passada apareceria como alguém que falta
    sempre — e puxaria a previsão inteira pra baixo.
    """
    linha = dados.buscar_um("SELECT data FROM refeicao WHERE id = ?", (refeicao_id,))
    if linha is None:
        return []
    data_atual = linha["data"]

    linhas = dados.buscar_todos(
        """
        WITH recentes AS (
            SELECT id, data
              FROM refeicao
             WHERE data < ?
             ORDER BY data DESC
             LIMIT ?
        )
        SELECT (SELECT COUNT(*)
                  FROM consumo c
                 WHERE c.aluno_id = a.id
                   AND c.refeicao_id IN (SELECT id FROM recentes)) AS consumos,
               (SELECT COUNT(*)
                  FROM recentes r
                 WHERE r.data >= date(a.criado_em))                AS oportunidades
          FROM aluno a
         WHERE a.ativo = 1
           AND a.id NOT IN (SELECT aluno_id FROM declaracao WHERE refeicao_id = ?)
        """,
        (data_atual, janela, refeicao_id),
    )
    return [(linha["consumos"], linha["oportunidades"]) for linha in linhas]


def taxa_media_escola(
    refeicao_id: int, janela: int = JANELA_HISTORICO
) -> float | None:
    """Proporção geral de comparecimento nas refeições recentes.

    É o valor usado para quem ainda não tem histórico próprio. Devolve None
    quando nem a escola tem histórico — caso do primeiro dia de uso.
    """
    linha = dados.buscar_um("SELECT data FROM refeicao WHERE id = ?", (refeicao_id,))
    if linha is None:
        return None

    resultado = dados.buscar_um(
        """
        WITH recentes AS (
            SELECT id, data
              FROM refeicao
             WHERE data < ?
             ORDER BY data DESC
             LIMIT ?
        )
        SELECT (SELECT COUNT(*) FROM consumo
                 WHERE refeicao_id IN (SELECT id FROM recentes))          AS consumos,
               (SELECT COALESCE(SUM(
                          (SELECT COUNT(*) FROM recentes r
                            WHERE r.data >= date(a.criado_em))), 0)
                  FROM aluno a WHERE a.ativo = 1)                          AS oportunidades
        """,
        (linha["data"], janela),
    )

    if not resultado or not resultado["oportunidades"]:
        return None
    return resultado["consumos"] / resultado["oportunidades"]
