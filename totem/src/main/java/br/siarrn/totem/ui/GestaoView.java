package br.siarrn.totem.ui;

import br.siarrn.totem.local.FilaOffline;
import br.siarrn.totem.rede.ApiClient;
import br.siarrn.totem.rede.PainelCozinha;
import javafx.animation.Timeline;
import javafx.animation.KeyFrame;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.VBox;
import javafx.util.Duration;

/**
 * O painel da cozinha.
 *
 * <p>Responde uma pergunta só — <b>quantos pratos preparar</b> — e põe todo o
 * resto em segundo plano. O número grande no meio da tela é o produto inteiro
 * do sistema; os detalhes embaixo existem para explicar de onde ele veio,
 * porque um número sem explicação é exatamente o que fez a escola parar de
 * acreditar no sistema anterior.
 *
 * <p>Depois do almoço, a linha que mais importa é a última: o previsto contra o
 * que de fato foi servido. É ela que, em algumas semanas, tira a margem de medo
 * do preparo — e margem de medo é o nome verdadeiro da sobra.
 */
public final class GestaoView {

    private static final Duration INTERVALO_ATUALIZACAO = Duration.seconds(15);

    private final ApiClient api;
    private final FilaOffline fila;
    private final Runnable aoVoltar;

    private final BorderPane raiz = new BorderPane();
    private final Label numeroPrevisto = new Label("—");
    private final Label explicacao = new Label();
    private final Label detalheDeclaracoes = new Label();
    private final Label detalheSilenciosos = new Label();
    private final Label servidosAgora = new Label();
    private final Label comparacao = new Label();
    private final Label cardapio = new Label();
    private final Label situacao = new Label();

    private Timeline relogio;

    public GestaoView(ApiClient api, FilaOffline fila, Runnable aoVoltar) {
        this.api = api;
        this.fila = fila;
        this.aoVoltar = aoVoltar;
        montar();
    }

    public Region raiz() {
        return raiz;
    }

    // -----------------------------------------------------------------------
    // Montagem
    // -----------------------------------------------------------------------
    private void montar() {
        raiz.getStyleClass().add("gestao");

        Label titulo = new Label("Cozinha");
        titulo.getStyleClass().add("titulo-gestao");

        Button voltar = new Button("Voltar ao totem");
        voltar.getStyleClass().add("botao-secundario");
        voltar.setOnAction(evento -> {
            parar();
            aoVoltar.run();
        });

        Button atualizar = new Button("Atualizar agora");
        atualizar.getStyleClass().add("botao-secundario");
        atualizar.setOnAction(evento -> atualizar());

        HBox topo = new HBox(14, titulo, espacador(), atualizar, voltar);
        topo.setAlignment(Pos.CENTER_LEFT);
        topo.setPadding(new Insets(20, 28, 10, 28));

        Label rotulo = new Label("preparar hoje");
        rotulo.getStyleClass().add("rotulo-destaque");

        numeroPrevisto.getStyleClass().add("numero-destaque");
        explicacao.getStyleClass().add("explicacao");
        explicacao.setWrapText(true);

        VBox destaque = new VBox(2, numeroPrevisto, rotulo, explicacao);
        destaque.setAlignment(Pos.CENTER);
        destaque.setPadding(new Insets(10, 40, 24, 40));

        for (Label linha : new Label[] {detalheDeclaracoes, detalheSilenciosos, cardapio}) {
            linha.getStyleClass().add("detalhe");
        }
        servidosAgora.getStyleClass().add("servidos");
        comparacao.getStyleClass().add("comparacao");
        comparacao.setWrapText(true);

        VBox detalhes = new VBox(9, detalheDeclaracoes, detalheSilenciosos, cardapio,
                new Region(), servidosAgora, comparacao);
        detalhes.setAlignment(Pos.CENTER_LEFT);
        detalhes.setPadding(new Insets(0, 60, 10, 60));
        detalhes.setMaxWidth(720);

        VBox centro = new VBox(6, destaque, detalhes);
        centro.setAlignment(Pos.TOP_CENTER);

        situacao.getStyleClass().add("rodape");
        HBox rodape = new HBox(situacao);
        rodape.setPadding(new Insets(12, 28, 16, 28));

        raiz.setTop(topo);
        raiz.setCenter(centro);
        raiz.setBottom(rodape);
    }

    private static Region espacador() {
        Region vazio = new Region();
        HBox.setHgrow(vazio, Priority.ALWAYS);
        return vazio;
    }

    // -----------------------------------------------------------------------
    // Ciclo de vida
    // -----------------------------------------------------------------------
    /** Começa a atualizar sozinho. A cozinha não deve precisar clicar em nada. */
    public void iniciar() {
        atualizar();
        relogio = new Timeline(new KeyFrame(INTERVALO_ATUALIZACAO, evento -> atualizar()));
        relogio.setCycleCount(Timeline.INDEFINITE);
        relogio.play();
    }

    public void parar() {
        if (relogio != null) {
            relogio.stop();
            relogio = null;
        }
    }

    // -----------------------------------------------------------------------
    // Atualização
    // -----------------------------------------------------------------------
    private void atualizar() {
        // Consulta fora da thread da interface: se o servidor demorar, a janela
        // não pode congelar na frente de quem está esperando o número.
        Thread.ofVirtual().start(() -> {
            try {
                PainelCozinha painel = api.painelDeHoje();
                Platform.runLater(() -> preencher(painel));
            } catch (ApiClient.ApiIndisponivelException erro) {
                Platform.runLater(() -> semServidor(erro.getMessage()));
            }
        });
    }

    private void preencher(PainelCozinha painel) {
        numeroPrevisto.setText(String.valueOf(painel.previsto()));
        explicacao.setText(painel.explicacaoDaConfianca());

        detalheDeclaracoes.setText(
                "Confirmaram presença: " + painel.sim()
                        + "     ·     Avisaram ausência: " + painel.nao());

        detalheSilenciosos.setText(
                "Não declararam: " + painel.silenciosos()
                        + "  —  pelo histórico, devem aparecer cerca de "
                        + Math.round(painel.silenciososEstimados()));

        cardapio.setText(painel.cardapio() == null || painel.cardapio().isBlank()
                ? "Cardápio de hoje ainda não informado."
                : "Cardápio: " + painel.cardapio());

        servidosAgora.setText("Já almoçaram: " + painel.consumidos());
        comparacao.setText(textoDaComparacao(painel));

        situacao.setText("Atualizado agora  ·  " + painel.totalAlunos()
                + " alunos na base  ·  " + pendentesTexto());
    }

    /**
     * A frase que fecha o ciclo do dia.
     *
     * <p>Só faz sentido depois que a fila passou: comparar previsão com consumo
     * às onze da manhã diria apenas que ninguém almoçou ainda.
     */
    private String textoDaComparacao(PainelCozinha painel) {
        if (painel.consumidos() == 0) {
            return "A comparação entre previsto e servido aparece conforme a fila anda.";
        }

        int erro = painel.erroDaPrevisao();
        if (erro == 0) {
            return "A previsão bateu exatamente com o que foi servido.";
        }
        if (erro < 0) {
            return "Até agora, " + Math.abs(erro) + " a menos que o previsto.";
        }
        return "Já passou " + erro + " do previsto.";
    }

    private void semServidor(String motivo) {
        explicacao.setText("Sem contato com o servidor — mostrando o último número conhecido.");
        situacao.setText("Servidor fora do ar (" + motivo + ")  ·  " + pendentesTexto());
    }

    private String pendentesTexto() {
        int pendentes = fila.pendentes();
        return pendentes == 0 ? "fila sincronizada" : pendentes + " almoços a enviar";
    }
}
