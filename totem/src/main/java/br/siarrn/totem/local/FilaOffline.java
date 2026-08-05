package br.siarrn.totem.local;

import br.siarrn.totem.Config;
import br.siarrn.totem.rede.Aluno;
import br.siarrn.totem.rede.ApiClient;
import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * Fila de almoços ainda não enviados ao servidor.
 *
 * <p>É o requisito de sobrevivência do projeto. O totem <b>nunca</b> espera o
 * servidor para responder ao aluno: grava a passagem aqui, mostra a tela verde
 * na hora, e sincroniza quando der. Se a rede cair com cem pessoas na fila, a
 * fila continua andando — e é isso que determina se a cozinha vai confiar no
 * sistema no dia seguinte.
 *
 * <p>O formato é uma linha de JSON por almoço. Acrescentar uma linha ao fim de
 * um arquivo é a escrita mais difícil de corromper que existe: se faltar
 * energia no meio, perde-se no máximo o último registro, e o resto continua
 * legível.
 */
public final class FilaOffline {

    private static final Path ARQUIVO = Config.pastaLocal().resolve("fila.jsonl");

    private static final DateTimeFormatter FORMATO =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final Gson gson = new Gson();

    /**
     * Um almoço à espera de envio.
     *
     * <p>{@code alunoId} nulo significa aluno cadastrado com o servidor fora do
     * ar: só se sabe o nome, e o cadastro de verdade acontece na sincronização.
     * Sem isso, quem chegasse novo durante uma queda de rede ficaria sem almoçar
     * — e o sistema teria acabado de negar comida a um aluno.
     */
    private record Item(Integer alunoId, String nome, String turma, String registradoEm, String origem) {}

    public static String agora() {
        return LocalDateTime.now().format(FORMATO);
    }

    // -----------------------------------------------------------------------
    // Escrita
    // -----------------------------------------------------------------------
    private synchronized void acrescentar(Item item) {
        try {
            Files.createDirectories(ARQUIVO.getParent());
            Files.writeString(
                    ARQUIVO,
                    gson.toJson(item) + System.lineSeparator(),
                    StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.APPEND);
        } catch (IOException erro) {
            // Não há para onde escalar: a pessoa já está com o prato na mão.
            // Registrar no console é tudo o que dá pra fazer sem parar a fila.
            System.err.println("FALHA AO GRAVAR NA FILA LOCAL: " + erro.getMessage());
        }
    }

    /** Registra o almoço de um aluno que já existe na base. */
    public void registrar(Aluno aluno, String origem) {
        acrescentar(new Item(aluno.id(), null, null, agora(), origem));
    }

    /** Registra o almoço de alguém que acabou de se cadastrar com o servidor fora. */
    public void registrarCadastroPendente(String nome, String turma) {
        acrescentar(new Item(null, nome, turma, agora(), "nome"));
    }

    // -----------------------------------------------------------------------
    // Sincronização
    // -----------------------------------------------------------------------
    public synchronized int pendentes() {
        return ler().size();
    }

    private List<Item> ler() {
        if (!Files.isRegularFile(ARQUIVO)) {
            return List.of();
        }
        List<Item> itens = new ArrayList<>();
        try {
            for (String linha : Files.readAllLines(ARQUIVO, StandardCharsets.UTF_8)) {
                if (linha.isBlank()) {
                    continue;
                }
                try {
                    Item item = gson.fromJson(linha, Item.class);
                    if (item != null) {
                        itens.add(item);
                    }
                } catch (JsonSyntaxException erro) {
                    // Linha truncada por queda de energia. Descartar uma é melhor
                    // que travar a sincronização de todas as outras.
                    System.err.println("Linha ilegível na fila, descartada.");
                }
            }
        } catch (IOException erro) {
            System.err.println("Não foi possível ler a fila local: " + erro.getMessage());
        }
        return itens;
    }

    private void reescrever(List<Item> restantes) {
        try {
            if (restantes.isEmpty()) {
                Files.deleteIfExists(ARQUIVO);
                return;
            }
            Path temporario = ARQUIVO.resolveSibling("fila.jsonl.tmp");
            StringBuilder conteudo = new StringBuilder();
            for (Item item : restantes) {
                conteudo.append(gson.toJson(item)).append(System.lineSeparator());
            }
            Files.writeString(temporario, conteudo.toString(), StandardCharsets.UTF_8);
            Files.move(temporario, ARQUIVO, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException erro) {
            System.err.println("Não foi possível reescrever a fila: " + erro.getMessage());
        }
    }

    /**
     * Tenta enviar tudo o que está pendente.
     *
     * <p>Só remove da fila o que o servidor confirmou. Reenviar um almoço já
     * registrado é inofensivo — a rota de consumo é idempotente do outro lado —,
     * então na dúvida o item permanece e tenta de novo. O erro que não se pode
     * cometer é o contrário: apagar da fila algo que nunca chegou.
     *
     * @return quantos foram sincronizados nesta rodada
     */
    public synchronized int sincronizar(ApiClient api, BaseLocal base) {
        List<Item> itens = ler();
        if (itens.isEmpty()) {
            return 0;
        }

        List<Item> restantes = new ArrayList<>();
        int enviados = 0;

        for (Item item : itens) {
            try {
                Integer alunoId = item.alunoId();

                if (alunoId == null) {
                    // Aluno cadastrado enquanto o servidor estava fora: cria agora.
                    Aluno criado = api.cadastrar(item.nome(), item.turma() == null ? "" : item.turma());
                    base.acrescentar(criado);
                    alunoId = criado.id();
                }

                api.registrarConsumo(alunoId, item.registradoEm(), item.origem());
                enviados++;
            } catch (ApiClient.ApiIndisponivelException erro) {
                restantes.add(item);
            }
        }

        reescrever(restantes);
        return enviados;
    }
}
