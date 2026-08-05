package br.siarrn.totem.rede;

import br.siarrn.totem.Config;
import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonSyntaxException;
import com.google.gson.reflect.TypeToken;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Conversa com o servidor do SIARRN.
 *
 * <p>Os tempos limite curtos são a decisão de projeto mais importante desta
 * classe. Um totem que espera dez segundos por uma resposta trava a fila do
 * almoço, e uma fila travada faz a cozinha desistir do sistema no primeiro dia.
 * Nada aqui pode demorar mais que dois segundos: se a rede não responder nesse
 * prazo, quem chama trata como offline e segue em frente.
 */
public final class ApiClient {

    private static final Duration TEMPO_LIMITE = Duration.ofSeconds(2);

    /** Baixar a base inteira é mais pesado que uma consulta, e acontece fora da fila. */
    private static final Duration TEMPO_LIMITE_BASE = Duration.ofSeconds(15);

    private final Gson gson = new GsonBuilder()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create();

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(TEMPO_LIMITE)
            .build();

    private final Config config;

    public ApiClient(Config config) {
        this.config = config;
    }

    // -----------------------------------------------------------------------
    // Infraestrutura
    // -----------------------------------------------------------------------
    private HttpRequest.Builder pedido(String caminho, Duration limite) {
        HttpRequest.Builder construtor = HttpRequest.newBuilder()
                .uri(URI.create(config.servidor() + caminho))
                .timeout(limite)
                .header("Content-Type", "application/json");

        String token = config.token();
        if (!token.isBlank()) {
            construtor.header("Authorization", "Bearer " + token);
        }
        return construtor;
    }

    private String obter(String caminho, Duration limite) throws ApiIndisponivelException {
        try {
            HttpResponse<String> resposta =
                    http.send(pedido(caminho, limite).GET().build(),
                            HttpResponse.BodyHandlers.ofString());

            if (resposta.statusCode() == 404) {
                return null;
            }
            if (resposta.statusCode() >= 400) {
                throw new ApiIndisponivelException("Servidor respondeu " + resposta.statusCode());
            }
            return resposta.body();
        } catch (java.io.IOException erro) {
            throw new ApiIndisponivelException(erro.getMessage());
        } catch (InterruptedException erro) {
            Thread.currentThread().interrupt();
            throw new ApiIndisponivelException("Consulta interrompida");
        }
    }

    private String enviar(String caminho, Object corpo) throws ApiIndisponivelException {
        try {
            HttpResponse<String> resposta = http.send(
                    pedido(caminho, TEMPO_LIMITE)
                            .POST(HttpRequest.BodyPublishers.ofString(gson.toJson(corpo)))
                            .build(),
                    HttpResponse.BodyHandlers.ofString());

            if (resposta.statusCode() >= 400) {
                throw new ApiIndisponivelException(
                        "Servidor respondeu " + resposta.statusCode() + ": " + resposta.body());
            }
            return resposta.body();
        } catch (java.io.IOException erro) {
            throw new ApiIndisponivelException(erro.getMessage());
        } catch (InterruptedException erro) {
            Thread.currentThread().interrupt();
            throw new ApiIndisponivelException("Envio interrompido");
        }
    }

    // -----------------------------------------------------------------------
    // Rotas
    // -----------------------------------------------------------------------
    /** Diz se o servidor está no ar. Nunca lança: a resposta é o próprio booleano. */
    public boolean noAr() {
        try {
            return obter("/api/ping", TEMPO_LIMITE) != null;
        } catch (ApiIndisponivelException erro) {
            return false;
        }
    }

    /**
     * Baixa a base completa de alunos.
     *
     * <p>O totem guarda essa lista em disco e faz toda a busca em memória. É o
     * que permite a fila continuar andando com a rede caída — nenhuma tecla
     * digitada depende do servidor.
     */
    public List<Aluno> baixarBase() throws ApiIndisponivelException {
        String corpo = obter("/api/alunos/todos", TEMPO_LIMITE_BASE);
        if (corpo == null) {
            throw new ApiIndisponivelException("Base de alunos indisponível");
        }
        try {
            return gson.fromJson(corpo, new TypeToken<List<Aluno>>() {}.getType());
        } catch (JsonSyntaxException erro) {
            throw new ApiIndisponivelException("Resposta inesperada do servidor");
        }
    }

    /** Cadastra um aluno novo e devolve o registro criado, já com o código. */
    public Aluno cadastrar(String nome, String turma) throws ApiIndisponivelException {
        String corpo = enviar("/api/alunos", Map.of("nome", nome, "turma", turma));
        return gson.fromJson(corpo, Aluno.class);
    }

    /**
     * Registra que o aluno almoçou.
     *
     * <p>O horário é o do momento em que a pessoa passou pelo totem, não o do
     * envio: um almoço registrado offline às 11h47 e sincronizado às 12h30
     * continua sendo das 11h47.
     */
    public void registrarConsumo(int alunoId, String registradoEm, String origem)
            throws ApiIndisponivelException {
        enviar("/api/consumo", Map.of(
                "aluno_id", alunoId,
                "registrado_em", registradoEm,
                "origem", origem));
    }

    public PainelCozinha painelDeHoje() throws ApiIndisponivelException {
        String corpo = obter("/api/cozinha/hoje", TEMPO_LIMITE);
        if (corpo == null) {
            throw new ApiIndisponivelException("Painel indisponível");
        }
        return gson.fromJson(corpo, PainelCozinha.class);
    }

    /** Falha de comunicação com o servidor. Sempre recuperável: o totem segue offline. */
    public static class ApiIndisponivelException extends Exception {
        private static final long serialVersionUID = 1L;

        public ApiIndisponivelException(String mensagem) {
            super(mensagem);
        }
    }
}
