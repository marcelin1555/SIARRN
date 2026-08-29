package br.rn.cefe.siarrn

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch

/** Em que ponto o app está. */
enum class Etapa {
    /** Ninguém disse onde fica o servidor da escola. */
    ESCOLHENDO_SERVIDOR,

    /** O aparelho ainda não sabe de quem é. */
    ESCOLHENDO_ALUNO,

    /** Tudo pronto: cardápio, declaração e QR. */
    PRONTO,
}

/**
 * O estado do app, num lugar só.
 *
 * Três telas e duas rotas não pedem arquitetura em camadas. O que este modelo
 * precisa garantir é uma coisa: **a tela nunca trava esperando a rede**. Toda
 * chamada tem um estado de carregando e um de falha explicável, porque a rede
 * da escola cai, e o aluno com o celular na mão precisa entender o que houve.
 */
class AlmocoViewModel(private val prefs: Preferencias) : ViewModel() {

    var etapa by mutableStateOf(
        when {
            !prefs.temServidor -> Etapa.ESCOLHENDO_SERVIDOR
            !prefs.temAluno -> Etapa.ESCOLHENDO_ALUNO
            else -> Etapa.PRONTO
        }
    )
        private set

    var carregando by mutableStateOf(false)
        private set

    var recado by mutableStateOf("")
        private set

    var hoje by mutableStateOf<Hoje?>(null)
        private set

    var encontrados by mutableStateOf<List<Aluno>>(emptyList())
        private set

    val nome: String get() = prefs.alunoNome
    val turma: String get() = prefs.alunoTurma
    val codigo: String get() = prefs.alunoCodigo
    val servidor: String get() = prefs.servidor

    private fun api() = Api(prefs.servidor)

    // -----------------------------------------------------------------------
    // Servidor
    // -----------------------------------------------------------------------
    fun definirServidor(endereco: String) {
        val limpo = endereco.trim().let {
            if (it.startsWith("http://") || it.startsWith("https://")) it else "http://$it"
        }

        carregando = true
        recado = ""
        viewModelScope.launch {
            val respondeu = Api(limpo.trimEnd('/')).conferir()
            carregando = false

            if (!respondeu) {
                recado = "Não consegui falar com esse endereço. Confira o número e " +
                    "se o celular está no Wi-Fi da escola."
                return@launch
            }

            prefs.servidor = limpo
            etapa = if (prefs.temAluno) Etapa.PRONTO else Etapa.ESCOLHENDO_ALUNO
            if (etapa == Etapa.PRONTO) atualizar()
        }
    }

    // -----------------------------------------------------------------------
    // Quem sou eu
    // -----------------------------------------------------------------------
    fun buscar(termo: String) {
        if (termo.trim().length < 2) {
            encontrados = emptyList()
            return
        }
        viewModelScope.launch {
            encontrados = try {
                api().buscar(termo)
            } catch (erro: ErroDeRede) {
                recado = "Sem conexão com a escola."
                emptyList()
            }
        }
    }

    fun escolher(aluno: Aluno) {
        prefs.guardarAluno(aluno)
        encontrados = emptyList()
        recado = ""
        etapa = Etapa.PRONTO
        atualizar()
    }

    fun cadastrar(nome: String, turma: String) {
        carregando = true
        recado = ""
        viewModelScope.launch {
            try {
                escolher(api().cadastrar(nome, turma))
            } catch (erro: ErroDeRede) {
                recado = "Não deu para cadastrar agora: ${erro.message}"
            } finally {
                carregando = false
            }
        }
    }

    fun trocarDeAluno() {
        prefs.esquecerAluno()
        hoje = null
        encontrados = emptyList()
        recado = ""
        etapa = Etapa.ESCOLHENDO_ALUNO
    }

    // -----------------------------------------------------------------------
    // O dia
    // -----------------------------------------------------------------------
    fun atualizar() {
        if (etapa != Etapa.PRONTO) return

        carregando = true
        viewModelScope.launch {
            try {
                hoje = api().hoje(prefs.alunoCodigo)
                recado = ""
            } catch (erro: ErroDeRede) {
                // O QR continua na tela mesmo sem rede — é ele que resolve a
                // fila, e ele não depende de conexão nenhuma para ser mostrado.
                recado = "Sem conexão com a escola. Seu código continua valendo no totem."
            } finally {
                carregando = false
            }
        }
    }

    fun declarar(vai: Boolean) {
        val alvo = hoje ?: return

        carregando = true
        viewModelScope.launch {
            try {
                api().declarar(prefs.alunoId, vai)
                hoje = alvo.copy(declarou = vai)
                recado = ""
            } catch (erro: ErroDeRede) {
                recado = "Não deu para avisar a cozinha agora. Tente daqui a pouco."
            } finally {
                carregando = false
            }
        }
    }

    fun limparRecado() {
        recado = ""
    }
}
