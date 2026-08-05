package br.siarrn.totem.local;

import br.siarrn.totem.Config;
import br.siarrn.totem.rede.Aluno;
import br.siarrn.totem.rede.ApiClient;
import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Cópia local da lista de alunos.
 *
 * <p>Esta classe é o motivo de o totem não travar quando a rede cai. Toda busca
 * acontece aqui, em memória, sobre uma lista guardada em disco — nenhuma tecla
 * digitada na fila depende do servidor. O servidor só é procurado uma vez por
 * dia, para atualizar a lista, e mesmo esse contato é opcional: sem ele, o
 * totem trabalha com a cópia da última vez que conseguiu falar.
 */
public final class BaseLocal {

    private static final Path ARQUIVO = Config.pastaLocal().resolve("alunos.json");

    /** Duas letras é o mínimo. Uma só traria meia escola pra tela. */
    private static final int MINIMO_PARA_BUSCAR = 2;

    private static final int LIMITE_RESULTADOS = 20;

    private final Gson gson = new GsonBuilder()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create();

    private final List<Aluno> alunos = Collections.synchronizedList(new ArrayList<>());

    public BaseLocal() {
        carregarDoDisco();
    }

    // -----------------------------------------------------------------------
    // Persistência
    // -----------------------------------------------------------------------
    private void carregarDoDisco() {
        if (!Files.isRegularFile(ARQUIVO)) {
            return;
        }
        try {
            String conteudo = Files.readString(ARQUIVO, StandardCharsets.UTF_8);
            List<Aluno> lidos = gson.fromJson(conteudo, new TypeToken<List<Aluno>>() {}.getType());
            if (lidos != null) {
                alunos.clear();
                alunos.addAll(lidos);
            }
        } catch (IOException | RuntimeException erro) {
            System.err.println("Base local ilegível, seguindo vazia: " + erro.getMessage());
        }
    }

    private void salvarNoDisco() {
        try {
            Files.createDirectories(ARQUIVO.getParent());
            // Escreve num temporário e renomeia: se faltar energia no meio da
            // gravação, o arquivo bom continua lá em vez de virar um pela metade.
            Path temporario = ARQUIVO.resolveSibling("alunos.json.tmp");
            synchronized (alunos) {
                Files.writeString(temporario, gson.toJson(alunos), StandardCharsets.UTF_8);
            }
            Files.move(temporario, ARQUIVO, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException erro) {
            System.err.println("Não foi possível salvar a base local: " + erro.getMessage());
        }
    }

    /**
     * Atualiza a lista a partir do servidor.
     *
     * @return true se conseguiu; false se o servidor não respondeu — caso em que
     *     a cópia anterior continua valendo e o totem segue funcionando.
     */
    public boolean atualizar(ApiClient api) {
        try {
            List<Aluno> novos = api.baixarBase();
            if (novos == null || novos.isEmpty()) {
                return false;
            }
            synchronized (alunos) {
                alunos.clear();
                alunos.addAll(novos);
            }
            salvarNoDisco();
            return true;
        } catch (ApiClient.ApiIndisponivelException erro) {
            return false;
        }
    }

    /** Acrescenta um aluno recém-cadastrado sem precisar rebaixar a base inteira. */
    public void acrescentar(Aluno aluno) {
        alunos.add(aluno);
        salvarNoDisco();
    }

    // -----------------------------------------------------------------------
    // Busca
    // -----------------------------------------------------------------------
    /**
     * Reduz o texto à forma comparável: minúsculo, sem acento, sem espaço extra.
     *
     * <p>Precisa dar exatamente o mesmo resultado que {@code alunos.normalizar}
     * no servidor. Se as duas divergirem, um aluno encontrado pelo app some no
     * totem — e o problema aparece justamente na frente da fila.
     */
    public static String normalizar(String texto) {
        if (texto == null) {
            return "";
        }
        String semAcento = Normalizer.normalize(texto, Normalizer.Form.NFKD)
                .replaceAll("\\p{M}+", "");
        return semAcento.toLowerCase(Locale.ROOT).trim().replaceAll("\\s+", " ");
    }

    /**
     * Alunos cujo nome começa pelo termo, ou que tenham alguma palavra começando por ele.
     *
     * <p>"sil" encontra "João Silva" e "Ana Silveira", mas não "Basílio": casar
     * no meio da palavra encheria a tela de gente errada, e quem está na fila
     * digita o começo do primeiro nome ou do sobrenome.
     */
    public List<Aluno> buscar(String termo) {
        String alvo = normalizar(termo);
        if (alvo.length() < MINIMO_PARA_BUSCAR) {
            return List.of();
        }

        List<Aluno> encontrados = new ArrayList<>();
        synchronized (alunos) {
            for (Aluno aluno : alunos) {
                String comparavel = aluno.nomeBusca() != null && !aluno.nomeBusca().isBlank()
                        ? aluno.nomeBusca()
                        : normalizar(aluno.nome());

                if (comparavel.startsWith(alvo) || comparavel.contains(" " + alvo)) {
                    encontrados.add(aluno);
                    if (encontrados.size() >= LIMITE_RESULTADOS) {
                        break;
                    }
                }
            }
        }
        encontrados.sort((a, b) -> a.nome().compareToIgnoreCase(b.nome()));
        return encontrados;
    }

    /**
     * Alguns alunos quaisquer da base.
     *
     * <p>Existe para o diagnóstico simular a fila do almoço. A busca não serve
     * para isso: ela exige um termo, e qualquer termo escolhido enviesaria a
     * amostra para um pedaço do alfabeto.
     */
    public List<Aluno> amostra(int quantos) {
        synchronized (alunos) {
            return List.copyOf(alunos.subList(0, Math.min(quantos, alunos.size())));
        }
    }

    public int tamanho() {
        return alunos.size();
    }

    public boolean vazia() {
        return alunos.isEmpty();
    }
}
