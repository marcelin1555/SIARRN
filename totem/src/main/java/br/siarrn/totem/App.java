package br.siarrn.totem;

import br.siarrn.totem.local.BaseLocal;
import br.siarrn.totem.local.FilaOffline;
import br.siarrn.totem.rede.ApiClient;
import br.siarrn.totem.ui.DialogoPin;
import br.siarrn.totem.ui.GestaoView;
import br.siarrn.totem.ui.TotemView;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.scene.Scene;
import javafx.scene.input.KeyCode;
import javafx.scene.input.KeyCodeCombination;
import javafx.scene.input.KeyCombination;
import javafx.stage.Stage;

/**
 * SIARRN — totem da fila e painel da cozinha, no mesmo programa.
 *
 * <p>Um binário, dois modos. A escola instala onde precisar: em duas máquinas,
 * se tiver duas; alternando na mesma, se só houver uma. Como o equipamento
 * ainda não está definido, essa flexibilidade não é luxo — é o que permite o
 * sistema existir antes de a direção liberar qualquer coisa.
 *
 * <p>Argumentos aceitos:
 *
 * <pre>
 *   --servidor=http://192.168.0.10:8770   grava o endereço do servidor
 *   --gestao                              abre direto no painel da cozinha
 *   --janela                              não usa tela cheia (desenvolvimento)
 * </pre>
 */
public final class App extends Application {

    /** De quanto em quanto tempo a fila local tenta se esvaziar. */
    private static final int INTERVALO_SINCRONIZACAO_SEGUNDOS = 20;

    /** A base de alunos muda pouco; uma vez por hora é mais que suficiente. */
    private static final int INTERVALO_BASE_MINUTOS = 60;

    private Config config;
    private ApiClient api;
    private BaseLocal base;
    private FilaOffline fila;

    private TotemView totem;
    private GestaoView gestao;
    private Scene cena;
    private Stage palco;

    private ScheduledExecutorService agendador;

    @Override
    public void start(Stage palco) {
        this.palco = palco;

        config = new Config();
        aplicarArgumentos();

        api = new ApiClient(config);
        base = new BaseLocal();
        fila = new FilaOffline();

        totem = new TotemView(base, fila, api, this::abrirGestao);
        cena = new Scene(totem.raiz(), 1100, 740);
        cena.getStylesheets().add(
                App.class.getResource("/br/siarrn/totem/estilo.css").toExternalForm());

        // Atalho alternativo ao toque triplo no rodapé: em máquina com teclado,
        // é mais rápido para quem trabalha na cozinha.
        cena.getAccelerators().put(
                new KeyCodeCombination(KeyCode.G, KeyCombination.CONTROL_DOWN, KeyCombination.ALT_DOWN),
                this::abrirGestao);

        palco.setTitle("SIARRN");
        palco.setScene(cena);
        configurarTelaCheia();
        palco.show();

        totem.focar();
        iniciarTarefasDeFundo();

        if (getParameters().getUnnamed().contains("--gestao")) {
            abrirGestao(true);
        }
    }

    private void aplicarArgumentos() {
        List<String> argumentos = getParameters().getUnnamed();
        boolean mudou = false;

        for (String argumento : argumentos) {
            if (argumento.startsWith("--servidor=")) {
                config.definirServidor(argumento.substring("--servidor=".length()));
                mudou = true;
            }
        }
        if (mudou) {
            config.salvar();
        }
    }

    private void configurarTelaCheia() {
        if (getParameters().getUnnamed().contains("--janela")) {
            return;
        }
        palco.setFullScreen(true);
        palco.setFullScreenExitHint("");
        // Sem saída visível e sem ESC: o totem fica sozinho numa fila com cem
        // adolescentes, e minimizar a janela não pode ser uma das opções deles.
        palco.setFullScreenExitKeyCombination(KeyCombination.NO_MATCH);
    }

    // -----------------------------------------------------------------------
    // Alternância de modo
    // -----------------------------------------------------------------------
    private void abrirGestao() {
        abrirGestao(false);
    }

    private void abrirGestao(boolean semPin) {
        if (!semPin && !DialogoPin.pedirEConferir(palco, config.pin())) {
            return;
        }
        gestao = new GestaoView(api, fila, this::voltarAoTotem);
        cena.setRoot(gestao.raiz());
        gestao.iniciar();
    }

    private void voltarAoTotem() {
        if (gestao != null) {
            gestao.parar();
            gestao = null;
        }
        cena.setRoot(totem.raiz());
        totem.atualizarRodape();
        totem.focar();
    }

    // -----------------------------------------------------------------------
    // Tarefas de fundo
    // -----------------------------------------------------------------------
    private void iniciarTarefasDeFundo() {
        agendador = Executors.newScheduledThreadPool(2, tarefa -> {
            Thread linha = new Thread(tarefa, "siarrn-fundo");
            linha.setDaemon(true); // não segura o fechamento do programa
            return linha;
        });

        // Sincronização da fila. Roda sempre, mesmo sem rede: quando o servidor
        // voltar, a próxima passagem esvazia o que ficou acumulado sozinha.
        agendador.scheduleWithFixedDelay(
                this::sincronizar, 3, INTERVALO_SINCRONIZACAO_SEGUNDOS, TimeUnit.SECONDS);

        // Atualização da base de alunos, começando imediatamente.
        agendador.scheduleWithFixedDelay(
                () -> base.atualizar(api), 0, INTERVALO_BASE_MINUTOS, TimeUnit.MINUTES);
    }

    private void sincronizar() {
        try {
            int enviados = fila.sincronizar(api, base);
            if (enviados > 0) {
                Platform.runLater(() -> totem.atualizarRodape());
            }
        } catch (RuntimeException erro) {
            // Uma falha aqui não pode derrubar o agendador: se a tarefa morre,
            // a fila para de esvaziar em silêncio e ninguém percebe até o fim
            // do dia.
            System.err.println("Erro na sincronização: " + erro.getMessage());
        }
    }

    @Override
    public void stop() {
        if (agendador != null) {
            agendador.shutdownNow();
        }
        // Última tentativa de entregar o que ainda estiver na fila.
        fila.sincronizar(api, base);
    }

    public static void main(String[] argumentos) {
        launch(argumentos);
    }
}
