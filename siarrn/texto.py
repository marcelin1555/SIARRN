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

import unicodedata


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
