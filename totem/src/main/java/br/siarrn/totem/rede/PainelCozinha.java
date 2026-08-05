package br.siarrn.totem.rede;

/**
 * O que a cozinha precisa saber hoje.
 *
 * <p>Espelha a resposta de {@code GET /api/cozinha/hoje}. O campo que importa é
 * {@code previsto} — todos os outros existem para explicar de onde ele veio,
 * porque um número sem explicação é o que fez a escola parar de acreditar no
 * sistema anterior.
 */
public record PainelCozinha(
        int previsto,
        int sim,
        int nao,
        int silenciosos,
        double silenciososEstimados,
        int consumidos,
        int totalAlunos,
        String confianca,
        String cardapio,
        String data) {

    /** Texto honesto sobre o quanto dá pra confiar no número de hoje. */
    public String explicacaoDaConfianca() {
        return switch (confianca == null ? "" : confianca) {
            case "boa" -> "Baseado no hábito observado dos alunos.";
            case "parcial" -> "Ainda apoiado na média da escola para boa parte dos alunos.";
            case "sem_dados" -> "Sem histórico ainda — hoje o sistema conta todo mundo.";
            default -> "";
        };
    }

    /** Diferença entre o previsto e o que de fato foi servido. */
    public int erroDaPrevisao() {
        return consumidos - previsto;
    }
}
