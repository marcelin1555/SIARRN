"""
SIARRN — Base fictícia para testes e demonstração

Gera alunos, um mês de refeições passadas e o histórico de consumo de cada um.
O histórico é o ponto: sem ele a previsão não tem o que exercitar, e o teste de
carga da fila não tem nomes de verdade para buscar.

Cada aluno recebe um perfil de frequência (quem almoça todo dia, quem aparece
de vez em quando), porque uma base onde todo mundo se comporta igual esconderia
justamente o erro que a previsão precisa acertar.

    python siarrn.py --seed
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from . import alunos, dados, refeicoes

# Semente fixa: a mesma base toda vez, para que um teste que falhou possa ser
# reproduzido e para que a demonstração não mude de números a cada execução.
SEMENTE = 20260804

QUANTIDADE_PADRAO = 120
DIAS_DE_HISTORICO = 20

_PRIMEIROS = [
    "Ana", "Beatriz", "Camila", "Daniela", "Eduarda", "Fernanda", "Gabriela",
    "Helena", "Isabela", "Júlia", "Larissa", "Mariana", "Natália", "Rafaela",
    "Sofia", "Vitória", "Yasmin", "Alice", "Clara", "Lívia", "Maria", "Emanuelly",
    "André", "Bruno", "Carlos", "Daniel", "Eduardo", "Felipe", "Gabriel",
    "Henrique", "Igor", "João", "Kaio", "Lucas", "Matheus", "Nathan", "Otávio",
    "Pedro", "Rafael", "Samuel", "Thiago", "Vinícius", "Wesley", "Davi", "Enzo",
]

_SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa",
    "Carvalho", "Almeida", "Nascimento", "Araújo", "Fernandes", "Ribeiro",
    "Rodrigues", "Gomes", "Martins", "Barbosa", "Rocha", "Dias", "Cavalcante",
    "Bezerra", "Medeiros", "Dantas", "Fonseca", "Azevedo", "Moura", "Freitas",
]

_TURMAS = ["1º A", "1º B", "1º C", "2º A", "2º B", "3º A", "3º B"]

_CARDAPIOS = [
    "Arroz, feijão, frango assado e salada",
    "Macarronada com carne moída",
    "Arroz, feijão, peixe cozido e legumes",
    "Baião de dois com carne de sol",
    "Arroz, feijão, ovo frito e vinagrete",
    "Galinha caipira com pirão",
    "Arroz, feijão, carne guisada e farofa",
    "Sopa de legumes com carne",
]

# Perfis de frequência: (rótulo, probabilidade mínima, máxima, fatia dos alunos).
# A soma das fatias é 1.0 e a média ponderada fica perto de 0,6 — mais ou menos
# o que se espera de uma escola onde sobra comida.
_PERFIS = [
    ("todo dia", 0.90, 1.00, 0.25),
    ("quase sempre", 0.60, 0.85, 0.35),
    ("às vezes", 0.30, 0.55, 0.25),
    ("raramente", 0.05, 0.25, 0.15),
]


def _dias_uteis(quantidade: int, ate: date) -> list[date]:
    """As últimas N datas de segunda a sexta, terminando no dia anterior a `ate`."""
    dias: list[date] = []
    cursor = ate - timedelta(days=1)
    while len(dias) < quantidade:
        if cursor.weekday() < 5:
            dias.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(dias)


def _nomes_unicos(sorteio: random.Random, quantidade: int) -> list[str]:
    """Nomes distintos, mas com homônimos parciais de propósito.

    A busca do totem precisa ser testada com vários "Silva" e com dois alunos
    de primeiro nome igual — é o que acontece de verdade numa escola.
    """
    nomes: set[str] = set()
    while len(nomes) < quantidade:
        primeiro = sorteio.choice(_PRIMEIROS)
        sobrenome = sorteio.choice(_SOBRENOMES)
        segundo = sorteio.choice(_SOBRENOMES)
        nome = f"{primeiro} {sobrenome}" if sobrenome == segundo else f"{primeiro} {sobrenome} {segundo}"
        nomes.add(nome)
    return sorted(nomes)


def _escolher_perfil(sorteio: random.Random) -> float:
    sorte = sorteio.random()
    acumulado = 0.0
    for _, minimo, maximo, fatia in _PERFIS:
        acumulado += fatia
        if sorte <= acumulado:
            return sorteio.uniform(minimo, maximo)
    return sorteio.uniform(0.6, 0.85)


def popular(
    quantidade: int = QUANTIDADE_PADRAO,
    dias: int = DIAS_DE_HISTORICO,
    declaracoes_hoje: bool = True,
) -> dict:
    """Cria a base fictícia. Não faz nada se já houver alunos cadastrados."""
    dados.init_db()

    if alunos.contar() > 0:
        return {"alunos": 0, "refeicoes": 0, "consumos": 0, "ja_existia": True}

    sorteio = random.Random(SEMENTE)
    hoje = date.today()
    datas = _dias_uteis(dias, hoje)
    primeira = datas[0]

    # --- alunos ---------------------------------------------------------
    # `criado_em` precisa ficar no passado: a previsão só conta como
    # "oportunidade" as refeições posteriores ao cadastro do aluno, então um
    # aluno criado hoje teria histórico zero e nada seria exercitado.
    # A escrita é feita numa conexão só. Abrir e fechar o banco a cada aluno e a
    # cada consumo transformaria o seed em milhares de conexões e uns bons
    # segundos de espera — o suficiente para desencorajar rodá-lo.
    perfis: dict[int, dict] = {}
    consumos = 0

    with dados.db_cursor() as cur:
        for nome in _nomes_unicos(sorteio, quantidade):
            # Uma parte entra depois do início, para exercitar quem tem pouco histórico.
            entrada = primeira - timedelta(days=1)
            if sorteio.random() < 0.10:
                entrada = sorteio.choice(datas[: max(1, len(datas) - 2)])

            cur.execute(
                """
                INSERT INTO aluno (nome, nome_busca, turma, codigo, criado_em)
                     VALUES (?, ?, ?, ?, ?)
                """,
                (
                    nome,
                    alunos.normalizar(nome),
                    sorteio.choice(_TURMAS),
                    alunos.gerar_codigo(),
                    f"{entrada.isoformat()} 07:00:00",
                ),
            )
            perfis[cur.lastrowid] = {
                "frequencia": _escolher_perfil(sorteio),
                "entrada": entrada,
            }

        # --- refeições passadas e consumos ------------------------------
        for indice, dia in enumerate(datas):
            cur.execute(
                "INSERT OR IGNORE INTO refeicao (data, turno, cardapio) VALUES (?, ?, ?)",
                (dia.isoformat(), refeicoes.TURNO_PADRAO, _CARDAPIOS[indice % len(_CARDAPIOS)]),
            )
            cur.execute(
                "SELECT id FROM refeicao WHERE data = ? AND turno = ?",
                (dia.isoformat(), refeicoes.TURNO_PADRAO),
            )
            refeicao_id = cur.fetchone()["id"]

            for aluno_id, perfil in perfis.items():
                if perfil["entrada"] > dia:
                    continue  # ainda não era aluno nesse dia
                if sorteio.random() <= perfil["frequencia"]:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO consumo
                               (aluno_id, refeicao_id, registrado_em, origem)
                             VALUES (?, ?, ?, 'nome')
                        """,
                        (aluno_id, refeicao_id, f"{dia.isoformat()} 11:{sorteio.randint(30, 59)}:00"),
                    )
                    consumos += 1

    # --- o dia de hoje --------------------------------------------------
    hoje_refeicao = refeicoes.garantir(hoje.isoformat())
    refeicoes.definir_cardapio(hoje_refeicao["id"], sorteio.choice(_CARDAPIOS))

    if declaracoes_hoje:
        # Cerca de 40% de adesão — o cenário realista, e o que mais interessa
        # testar: nem o caso fácil de todo mundo declarar, nem o de ninguém.
        with dados.db_cursor() as cur:
            for aluno_id, perfil in perfis.items():
                if sorteio.random() >= 0.40:
                    continue
                vai = sorteio.random() <= perfil["frequencia"]
                cur.execute(
                    """
                    INSERT OR REPLACE INTO declaracao
                           (aluno_id, refeicao_id, vai, declarado_em)
                         VALUES (?, ?, ?, ?)
                    """,
                    (aluno_id, hoje_refeicao["id"], 1 if vai else 0, refeicoes.agora()),
                )

    return {
        "alunos": len(perfis),
        "refeicoes": len(datas) + 1,
        "consumos": consumos,
        "ja_existia": False,
    }
