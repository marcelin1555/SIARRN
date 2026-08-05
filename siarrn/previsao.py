"""
SIARRN — Quantos pratos preparar

Este módulo não toca no banco de propósito: recebe números e devolve números.
É a peça que mais vai mudar conforme os dados reais chegarem, e a única do
sistema cuja correção dá pra provar sem subir servidor nenhum.

A regra
-------
Todo aluno cai em exatamente um de três grupos:

    declarou que vem       →  conta 1
    declarou que não vem   →  conta 0
    não declarou nada      →  conta a própria taxa histórica de comparecimento

    previsão = (quantos declararam SIM) + Σ (taxa histórica de cada silencioso)

O documento de design escreve essa regra como "sim + histórico − não". O
"menos" ali é conceitual: quem avisou ausência sai da conta porque não está
em nenhum dos dois outros grupos, e não porque seja subtraído de novo. Somar
e depois subtrair o mesmo grupo o tiraria duas vezes.

Por que isso importa
--------------------
O sistema anterior da escola morreu porque dependia de todo mundo declarar
todo dia. Aqui a declaração melhora a previsão, mas nunca a sustenta: com
adesão zero isto vira média histórica pura e ainda entrega número útil; com
adesão total vira contagem exata. Não existe entrada que faça a conta quebrar.
"""
from __future__ import annotations

import math

# Abaixo disso, a taxa individual do aluno é ruído: quem apareceu uma vez em
# uma oportunidade não "comparece 100% das vezes". Usa-se a média da escola até
# haver histórico próprio suficiente.
MINIMO_OPORTUNIDADES = 3

# Primeiro dia de uso: ninguém tem histórico e a escola também não. Assumir
# presença total superestima, mas errar pra cima no dia em que não se sabe nada
# é melhor do que mandar a cozinha preparar pouco e faltar comida.
TAXA_SEM_NENHUM_DADO = 1.0


def taxa_do_aluno(
    consumos: int, oportunidades: int, taxa_media: float | None
) -> tuple[float, bool]:
    """Probabilidade de um aluno silencioso aparecer.

    Devolve `(taxa, usou_fallback)`. O segundo valor é o que permite ao painel
    da cozinha dizer honestamente que a previsão ainda está se apoiando na
    média geral em vez de em hábito observado.
    """
    if oportunidades >= MINIMO_OPORTUNIDADES and oportunidades > 0:
        return consumos / oportunidades, False

    if taxa_media is None:
        return TAXA_SEM_NENHUM_DADO, True

    return taxa_media, True


def calcular(
    sim: int,
    nao: int,
    silenciosos: list[tuple[int, int]],
    taxa_media: float | None = None,
) -> dict:
    """Calcula quantos pratos preparar.

    Parâmetros
    ----------
    sim
        Quantos alunos declararam que vêm.
    nao
        Quantos avisaram ausência. Não entra na soma — está aqui porque a
        cozinha quer ver o número, e porque ele é o sinal de que o app está
        sendo usado.
    silenciosos
        Um par `(consumos, oportunidades)` por aluno que não declarou nada.
    taxa_media
        Comparecimento médio da escola nas refeições recentes, ou None se não
        houver histórico nenhum ainda.

    Devolve um dicionário pronto para o painel da cozinha, incluindo o nível de
    confiança — porque um número sem contexto é exatamente o que fez a escola
    parar de acreditar no sistema anterior.
    """
    estimativa = 0.0
    com_fallback = 0

    for consumos, oportunidades in silenciosos:
        taxa, usou_fallback = taxa_do_aluno(consumos, oportunidades, taxa_media)
        estimativa += taxa
        if usou_fallback:
            com_fallback += 1

    total = sim + estimativa

    # O `round` antes do `ceil` não é preciosismo. Dez alunos com taxa 0,7 somam
    # 7,000000000000001 em ponto flutuante, e o arredondamento pra cima viraria
    # 8 pratos — um prato a mais nascido de ruído binário, num sistema cujo
    # propósito é justamente reduzir sobra. Seis casas descartam o ruído e
    # preservam qualquer fração que seja real.
    return {
        "previsto": math.ceil(round(total, 6)),
        "sim": sim,
        "nao": nao,
        "silenciosos": len(silenciosos),
        "silenciosos_estimados": round(estimativa, 1),
        "taxa_media": round(taxa_media, 3) if taxa_media is not None else None,
        "confianca": _confianca(len(silenciosos), com_fallback, taxa_media),
    }


def _confianca(total_silenciosos: int, com_fallback: int, taxa_media: float | None) -> str:
    """Quanto a previsão está apoiada em hábito observado, e não em chute.

    'sem_dados' no começo, 'parcial' enquanto a maioria dos silenciosos ainda
    não tem histórico próprio, 'boa' quando a estimativa vem de comportamento
    real. A cozinha precisa saber a diferença antes de confiar no número.
    """
    if taxa_media is None:
        return "sem_dados"
    if total_silenciosos == 0:
        return "boa"
    if com_fallback / total_silenciosos > 0.5:
        return "parcial"
    return "boa"
