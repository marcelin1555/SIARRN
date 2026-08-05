package br.siarrn.totem.ui;

import java.util.Optional;
import javafx.geometry.Insets;
import javafx.scene.control.ButtonBar;
import javafx.scene.control.ButtonType;
import javafx.scene.control.Dialog;
import javafx.scene.control.Label;
import javafx.scene.control.TextField;
import javafx.scene.layout.GridPane;
import javafx.stage.Window;

/**
 * Cadastro de aluno na própria fila, em dez segundos.
 *
 * <p>Não existe carteirinha na escola e a secretaria não forneceu lista nenhuma:
 * a base do sistema se constrói aqui, um aluno por vez, na primeira vez que
 * cada um almoça. Por isso só há dois campos — qualquer coisa além disso vira
 * fila parada.
 */
public final class DialogoCadastro {

    /** O que o aluno informou. */
    public record DadosNovos(String nome, String turma) {}

    private final String nomeSugerido;

    public DialogoCadastro(String nomeSugerido) {
        this.nomeSugerido = nomeSugerido;
    }

    public Optional<DadosNovos> mostrar(Window dono) {
        Dialog<DadosNovos> dialogo = new Dialog<>();
        dialogo.initOwner(dono);
        dialogo.setTitle("Primeiro almoço");
        dialogo.setHeaderText("Vamos te cadastrar. É rápido e só acontece uma vez.");

        ButtonType confirmar = new ButtonType("Cadastrar e almoçar", ButtonBar.ButtonData.OK_DONE);
        dialogo.getDialogPane().getButtonTypes().addAll(confirmar, ButtonType.CANCEL);

        TextField campoNome = new TextField(nomeSugerido);
        campoNome.setPromptText("nome completo");
        campoNome.setPrefColumnCount(24);

        TextField campoTurma = new TextField();
        campoTurma.setPromptText("ex.: 2º A");

        GridPane grade = new GridPane();
        grade.setHgap(12);
        grade.setVgap(12);
        grade.setPadding(new Insets(18));
        grade.addRow(0, new Label("Nome"), campoNome);
        grade.addRow(1, new Label("Turma"), campoTurma);
        dialogo.getDialogPane().setContent(grade);
        dialogo.getDialogPane().getStyleClass().add("dialogo-cadastro");

        // Nome vazio não vira cadastro: um aluno sem nome é impossível de achar
        // depois e polui a base para sempre.
        dialogo.getDialogPane().lookupButton(confirmar).disableProperty()
                .bind(campoNome.textProperty().isEmpty());

        javafx.application.Platform.runLater(campoNome::requestFocus);

        dialogo.setResultConverter(botao -> botao == confirmar
                ? new DadosNovos(campoNome.getText().trim(), campoTurma.getText().trim())
                : null);

        return dialogo.showAndWait();
    }
}
