"""
SIARRN — Normalização de texto

Um módulo sozinho, sem dependência nenhuma, por um motivo concreto: esta
função é usada pelo servidor (que tem SQLite) e pelo totem (que roda em outra
máquina e não deve nem saber que existe banco de dados). Deixá-la em
`alunos.py` obrigaria o totem a importar a camada de dados inteira.

E ela precisa existir **uma vez só**. Enquanto o totem era em Java, esta regra
estava escrita duas vezes em duas linguagens; se as duas divergissem num
acento, um aluno cadastrado pelo servidor sumiria da busca do totem — e o erro
apareceria na frente da fila do almoço, no pior momento possível.
"""
from __future__ import annotations

import difflib
import unicodedata

# Medido em nomes reais: "Ana Lima" e "Ana Luiza" dão 0,82 e são pessoas
# diferentes; "Ana Lima" e "Ana Lina" dão 0,88 e são erro de digitação. Nenhum
# número separa tudo — "Gabriel Costa" e "Gabriela Costa" dão 0,96 — e por isso
# a lista vai para uma pessoa decidir, vendo a turma, e nunca mescla sozinha.
SEMELHANCA_MINIMA = 0.85


def normalizar(texto: str) -> str:
    """Reduz o nome à forma usada na busca: minúsculo, sem acento, sem espaço extra.

    É o que faz "joao", "João" e "JOAO" encontrarem a mesma pessoa. Numa fila de
    almoço ninguém vai acertar o acento — e não deveria precisar.
    """
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


def combina(nome_normalizado: str, termo_normalizado: str) -> bool:
    """Diz se um nome deve aparecer na busca por esse termo.

    Casa no início do nome completo ou no início de qualquer palavra dele:
    "sil" encontra "João Silva" e "Ana Silveira", mas não "Basílio". Casar no
    meio da palavra encheria a tela de gente errada, e quem está na fila digita
    o começo do primeiro nome ou do sobrenome.

    O servidor faz a mesma coisa em SQL (`LIKE 'termo%' OR LIKE '% termo%'`).
    As duas versões precisam concordar — os testes cobrem os dois lados.
    """
    if not termo_normalizado:
        return False
    return (
        nome_normalizado.startswith(termo_normalizado)
        or f" {termo_normalizado}" in nome_normalizado
    )


def _abrevia(curto: list[str], longo: list[str]) -> bool:
    """Cada palavra de `curto` começa uma palavra de `longo`, na mesma ordem.

    "maria s" abrevia "maria silva"; "joao pedro" abrevia "joao pedro lima".
    """
    posicao = 0
    for palavra in curto:
        while posicao < len(longo) and not longo[posicao].startswith(palavra):
            posicao += 1
        if posicao == len(longo):
            return False
        posicao += 1
    return True


def pares_suspeitos(alunos: list[dict], limite: int = 30) -> list[tuple[dict, dict]]:
    """Pares de cadastros que podem ser a mesma pessoa, os mais parecidos primeiro.

    Dois jeitos de o mesmo aluno virar dois cadastros na fila:

    * abreviou: "maria s" e "maria silva". O primeiro nome precisa ser igual —
      senão "maria" abreviaria "mariana".
    * errou a digitação, às vezes sem o último sobrenome: "jao pedro" e
      "joao pedro lima". Compara só as palavras que os dois têm.

    Quando um nome tem mais palavras que o outro, o mais curto precisa de duas:
    com uma só, "maria" casaria com todas as Marias da escola.

    shortcut: um par descartado pela cozinha volta a aparecer da próxima vez;
    guardar os descartes só se a lista encher de falsos positivos na prática.
    """
    nomes = [(a, (a.get("nome_busca") or normalizar(a.get("nome", ""))).split())
             for a in alunos]
    encontrados = []
    for i, (a, pa) in enumerate(nomes):
        for b, pb in nomes[i + 1:]:
            if not pa or not pb or pa[0][0] != pb[0][0]:
                continue
            n = min(len(pa), len(pb))
            if len(pa) != len(pb) and n < 2:
                continue
            if n >= 2 and pa[0] == pb[0] and (_abrevia(pa, pb) or _abrevia(pb, pa)):
                encontrados.append((1.0, a, b))
                continue
            comparador = difflib.SequenceMatcher(None, " ".join(pa[:n]), " ".join(pb[:n]))
            if comparador.quick_ratio() < SEMELHANCA_MINIMA:
                continue
            nota = comparador.ratio()
            if nota >= SEMELHANCA_MINIMA:
                encontrados.append((nota, a, b))

    encontrados.sort(key=lambda par: -par[0])
    return [(a, b) for _, a, b in encontrados[:limite]]
