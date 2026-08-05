package br.siarrn.totem;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/**
 * Configuração da máquina onde o totem está instalado.
 *
 * <p>Fica em {@code ~/.siarrn/totem.properties} porque é informação do
 * equipamento, não do projeto: o endereço do servidor e o PIN da cozinha mudam
 * de escola para escola e não podem viver dentro do código.
 */
public final class Config {

    private static final Path PASTA = Path.of(System.getProperty("user.home"), ".siarrn");
    private static final Path ARQUIVO = PASTA.resolve("totem.properties");

    private static final String PIN_PADRAO = "1234";
    private static final String SERVIDOR_PADRAO = "http://localhost:8770";

    private final Properties propriedades = new Properties();

    public Config() {
        carregar();
    }

    private void carregar() {
        if (!Files.isRegularFile(ARQUIVO)) {
            return;
        }
        try (InputStream entrada = Files.newInputStream(ARQUIVO)) {
            propriedades.load(entrada);
        } catch (IOException erro) {
            System.err.println("Não foi possível ler a configuração: " + erro.getMessage());
        }
    }

    public void salvar() {
        try {
            Files.createDirectories(PASTA);
            try (OutputStream saida = Files.newOutputStream(ARQUIVO)) {
                propriedades.store(saida, "SIARRN — configuração do totem");
            }
        } catch (IOException erro) {
            System.err.println("Não foi possível salvar a configuração: " + erro.getMessage());
        }
    }

    public String servidor() {
        return propriedades.getProperty("servidor", SERVIDOR_PADRAO);
    }

    public void definirServidor(String url) {
        propriedades.setProperty("servidor", url.trim().replaceAll("/+$", ""));
    }

    /**
     * PIN de entrada no modo gestão.
     *
     * <p>Não é segurança de verdade — é o que impede um aluno curioso de abrir o
     * painel da cozinha enquanto o totem está sozinho na fila.
     */
    public String pin() {
        return propriedades.getProperty("pin", PIN_PADRAO);
    }

    public void definirPin(String pin) {
        propriedades.setProperty("pin", pin.trim());
    }

    /** Token da API, quando a escola tiver configurado um. Vazio significa desligado. */
    public String token() {
        return propriedades.getProperty("token", "");
    }

    public void definirToken(String token) {
        propriedades.setProperty("token", token.trim());
    }

    public static Path pastaLocal() {
        return PASTA;
    }
}
