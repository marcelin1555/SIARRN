package br.siarrn.totem.rede;

/**
 * Um aluno, do jeito que o servidor devolve.
 *
 * <p>É um {@code record}: classe imutável cujos campos o compilador gera junto
 * com {@code equals}, {@code hashCode} e {@code toString}. Para dados que só
 * são lidos — como estes — evita dezenas de linhas de getters sem valor.
 *
 * <p>{@code nomeBusca} é o nome já normalizado pelo servidor (minúsculo, sem
 * acento). Guardá-lo pronto evita normalizar cento e vinte nomes a cada tecla
 * digitada na fila.
 */
public record Aluno(int id, String nome, String turma, String codigo, String nomeBusca) {

    /** Rótulo mostrado na lista de busca. A turma desempata homônimos. */
    public String rotulo() {
        return (turma == null || turma.isBlank()) ? nome : nome + "  ·  " + turma;
    }
}
