package br.rn.cefe.siarrn

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import br.rn.cefe.siarrn.ui.TelaEscolherAluno
import br.rn.cefe.siarrn.ui.TelaHoje
import br.rn.cefe.siarrn.ui.TelaServidor

/**
 * O app do aluno.
 *
 * Três telas e nenhuma navegação de verdade: qual delas aparece é consequência
 * do que o app já sabe. Sem endereço do servidor, pede o endereço; sem saber de
 * quem é o aparelho, pergunta; sabendo as duas coisas, mostra o dia.
 *
 * Navigation Compose resolveria idas e voltas que aqui não existem — ninguém
 * "volta" para a tela de configuração depois de configurar.
 */
class MainActivity : ComponentActivity() {

    private val modelo: AlmocoViewModel by lazy {
        val prefs = Preferencias(applicationContext)
        ViewModelProvider(
            this,
            viewModelFactory { initializer { AlmocoViewModel(prefs) } },
        )[AlmocoViewModel::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TemaSiarrn {
                Surface(Modifier.fillMaxSize()) { Conteudo(modelo) }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // O cardápio muda, e alguém pode ter avisado ausência pelo totem. Voltar
        // ao app é o momento natural de conferir — e é barato: duas chamadas.
        modelo.atualizar()
    }
}

@Composable
private fun Conteudo(modelo: AlmocoViewModel) {
    when (modelo.etapa) {
        Etapa.ESCOLHENDO_SERVIDOR -> TelaServidor(modelo)
        Etapa.ESCOLHENDO_ALUNO -> TelaEscolherAluno(modelo)
        Etapa.PRONTO -> TelaHoje(modelo)
    }
}
