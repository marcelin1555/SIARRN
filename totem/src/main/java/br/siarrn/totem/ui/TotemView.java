package br.siarrn.totem.ui;

import br.siarrn.totem.local.BaseLocal;
import br.siarrn.totem.local.FilaOffline;
import br.siarrn.totem.rede.Aluno;
import br.siarrn.totem.rede.ApiClient;
import java.util.List;
import javafx.animation.PauseTransition;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.TextField;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.util.Duration;

/**
 * A tela da fila do almoço.
 *
 * <p>Três regras governam tudo aqui:
 *
 * <ol>
 *   <li><b>Se resolve a três metros.</b> Quem está na fila enxerga a tela de
 *       longe e precisa entender sem ler instrução: nome grande, cor ocupando
 *       tudo, nenhum texto explicativo.
 *   <li><b>Nunca espera o servidor.</b> A busca é local e o registro vai para a
 *       fila em disco. A confirmação aparece na hora, com ou sem rede.
 *   <li><b>Ninguém vê vermelho.</b> O sistema não nega comida a aluno. Erro de
 *       rede é problema do totem, não do aluno, e ele não deveria nem perceber.
 * </ol>
 */
public final class TotemView {

    /** Tempo que a confirmação fica na tela antes de liberar o próximo da fila. */
    private static final Duration TEMPO_CONFIRMACAO = Duration.seconds(2.2);

    private final BaseLocal base;
    private final FilaOffline fila;
    private final ApiClient api;
    private final Runnable aoPedirGestao;

    private final StackPane raiz = new StackPane();
    private final TextField campoBusca = new TextField();
    private final VBox resultados = new VBox(10);
    private final Label rodape = new Label();

    private final BorderPane telaBusca = new BorderPane();
    private final VBox telaConfirmacao = new VBox(18);
    private final Label nomeConfirmado = new Label();
    private final Label mensagemConfirmacao = new Label();

    public TotemView(BaseLocal base, FilaOffline fila, ApiClient api, Runnable aoPedirGestao) {
        this.base = base;
        this.fila = fila;
        this.api = api;
        this.aoPedirGestao = aoPedirGestao;

        montarTelaBusca();
        montarTelaConfirmacao();

        raiz.getChildren().addAll(telaBusca, telaConfirmacao);
        raiz.getStyleClass().add("totem");
        telaConfirmacao.setVisible(false);
    }

    public Region raiz() {
        return raiz;
    }

    /** Devolve o foco ao campo de busca — a fila não pode depender de alguém clicar. */
    public void focar() {
        Platform.runLater(campoBusca::requestFocus);
    }

    // -----------------------------------------------------------------------
    // Tela de busca
    // -----------------------------------------------------------------------
    private void montarTelaBusca() {
        Label titulo = new Label("Digite seu nome");
        titulo.getStyleClass().add("titulo-totem");

        campoBusca.setPromptText("primeiras letras do nome ou do sobrenome");
        campoBusca.getStyleClass().add("campo-busca");
        campoBusca.textProperty().addListener((obs, antes, agora) -> atualizarResultados(agora));

        resultados.getStyleClass().add("resultados");
        resultados.setAlignment(Pos.TOP_CENTER);

        Button naoAchei = new Button("Não encontrei meu nome");
        naoAchei.getStyleClass().add("botao-secundario");
        naoAchei.setOnAction(evento -> abrirCadastro());

        VBox centro = new VBox(22, titulo, campoBusca, resultados);
        centro.setAlignment(Pos.TOP_CENTER);
        centro.setPadding(new Insets(60, 80, 20, 80));
        VBox.setVgrow(resultados, Priority.ALWAYS);

        rodape.getStyleClass().add("rodape");
        // Atalho discreto para a cozinha: o rodapé inteiro é clicável, mas nada
        // na tela sugere isso. Um aluno curioso não descobre por acidente.
        rodape.setOnMouseClicked(evento -> {
            if (evento.getClickCount() >= 3) {
                aoPedirGestao.run();
            }
        });

        HBox barra = new HBox(rodape, espacador(), naoAchei);
        barra.setAlignment(Pos.CENTER_LEFT);
        barra.setPadding(new Insets(14, 30, 18, 30));
        barra.getStyleClass().add("barra-inferior");

        telaBusca.setCenter(centro);
        telaBusca.setBottom(barra);
        atualizarRodape();
    }

    private static Region espacador() {
        Region vazio = new Region();
        HBox.setHgrow(vazio, Priority.ALWAYS);
        return vazio;
    }

    private void atualizarResultados(String termo) {
        resultados.getChildren().clear();

        List<Aluno> encontrados = base.buscar(termo);
        if (encontrados.isEmpty()) {
            return;
        }

        for (Aluno aluno : encontrados) {
            Button botao = new Button(aluno.rotulo());
            botao.getStyleClass().add("botao-aluno");
            botao.setMaxWidth(Double.MAX_VALUE);
            botao.setOnAction(evento -> registrar(aluno));
            resultados.getChildren().add(botao);
        }
    }

    // -----------------------------------------------------------------------
    // Registro
    // -----------------------------------------------------------------------
    private void registrar(Aluno aluno) {
        // Grava em disco e confirma na hora. O envio ao servidor é problema da
        // thread de sincronização, não de quem está com o prato na mão.
        fila.registrar(aluno, "nome");
        mostrarConfirmacao(aluno.nome(), "Bom almoço!");
    }

    private void mostrarConfirmacao(String nome, String mensagem) {
        nomeConfirmado.setText(nome);
        mensagemConfirmacao.setText(mensagem);

        telaConfirmacao.setVisible(true);
        telaBusca.setVisible(false);

        PauseTransition pausa = new PauseTransition(TEMPO_CONFIRMACAO);
        pausa.setOnFinished(evento -> voltarParaBusca());
        pausa.play();
    }

    private void voltarParaBusca() {
        telaConfirmacao.setVisible(false);
        telaBusca.setVisible(true);
        campoBusca.clear();
        resultados.getChildren().clear();
        atualizarRodape();
        focar();
    }

    private void montarTelaConfirmacao() {
        nomeConfirmado.getStyleClass().add("nome-confirmado");
        nomeConfirmado.setWrapText(true);
        mensagemConfirmacao.getStyleClass().add("mensagem-confirmacao");

        telaConfirmacao.getStyleClass().add("confirmacao");
        telaConfirmacao.setAlignment(Pos.CENTER);
        telaConfirmacao.setPadding(new Insets(40));
        telaConfirmacao.getChildren().addAll(nomeConfirmado, mensagemConfirmacao);
    }

    // -----------------------------------------------------------------------
    // Cadastro na hora
    // -----------------------------------------------------------------------
    private void abrirCadastro() {
        String sugestao = campoBusca.getText() == null ? "" : campoBusca.getText().trim();
        DialogoCadastro dialogo = new DialogoCadastro(sugestao);

        dialogo.mostrar(raiz.getScene().getWindow()).ifPresent(dadosNovos -> {
            Aluno criado = tentarCadastrarNoServidor(dadosNovos.nome(), dadosNovos.turma());

            if (criado != null) {
                base.acrescentar(criado);
                fila.registrar(criado, "nome");
            } else {
                // Servidor fora: guarda o cadastro junto com o almoço e resolve
                // os dois na sincronização. O aluno não pode ficar sem comer
                // porque a rede caiu.
                fila.registrarCadastroPendente(dadosNovos.nome(), dadosNovos.turma());
            }
            mostrarConfirmacao(dadosNovos.nome(), "Cadastrado. Bom almoço!");
        });
    }

    private Aluno tentarCadastrarNoServidor(String nome, String turma) {
        try {
            return api.cadastrar(nome, turma);
        } catch (ApiClient.ApiIndisponivelException erro) {
            return null;
        }
    }

    // -----------------------------------------------------------------------
    // Rodapé
    // -----------------------------------------------------------------------
    /** Estado do totem, em letras pequenas. Informação para a escola, não para o aluno. */
    public void atualizarRodape() {
        int pendentes = fila.pendentes();
        String situacao = pendentes == 0
                ? "tudo sincronizado"
                : pendentes + (pendentes == 1 ? " almoço a enviar" : " almoços a enviar");

        rodape.setText(base.tamanho() + " alunos  ·  " + situacao);
    }
}
