package br.siarrn.totem.ui;

import javafx.geometry.Insets;
import javafx.scene.control.ButtonBar;
import javafx.scene.control.ButtonType;
import javafx.scene.control.Dialog;
import javafx.scene.control.PasswordField;
import javafx.scene.layout.VBox;
import javafx.stage.Window;

/**
 * Entrada do modo gestão.
 *
 * <p>Não é segurança de verdade e não pretende ser: quem tiver acesso à máquina
 * pode ler o PIN no arquivo de configuração. O que ele evita é o cenário real —
 * o totem sozinho na fila, com cem adolescentes por perto, e o painel da cozinha
 * a um toque de distância.
 */
public final class DialogoPin {

    public static boolean pedirEConferir(Window dono, String pinEsperado) {
        Dialog<String> dialogo = new Dialog<>();
        dialogo.initOwner(dono);
        dialogo.setTitle("Cozinha");
        dialogo.setHeaderText("PIN de acesso");

        ButtonType entrar = new ButtonType("Entrar", ButtonBar.ButtonData.OK_DONE);
        dialogo.getDialogPane().getButtonTypes().addAll(entrar, ButtonType.CANCEL);

        PasswordField campo = new PasswordField();
        campo.setPromptText("PIN");

        VBox conteudo = new VBox(campo);
        conteudo.setPadding(new Insets(18));
        dialogo.getDialogPane().setContent(conteudo);

        javafx.application.Platform.runLater(campo::requestFocus);
        dialogo.setResultConverter(botao -> botao == entrar ? campo.getText() : null);

        return dialogo.showAndWait()
                .map(informado -> informado.equals(pinEsperado))
                .orElse(false);
    }

    private DialogoPin() {}
}
