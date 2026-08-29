package br.rn.cefe.siarrn

import android.content.Context

/**
 * O pouco que o app precisa lembrar entre uma abertura e outra: o endereço do
 * servidor da escola e quem é o dono do aparelho.
 *
 * `SharedPreferences` e não DataStore: são cinco valores lidos na abertura da
 * tela, sem concorrência e sem fluxo reativo. DataStore resolveria problemas
 * que este app não tem, ao custo de mais uma dependência num APK que precisa
 * ser pequeno.
 */
class Preferencias(contexto: Context) {

    private val prefs = contexto.getSharedPreferences("siarrn", Context.MODE_PRIVATE)

    var servidor: String
        get() = prefs.getString("servidor", "") ?: ""
        set(valor) {
            prefs.edit().putString("servidor", valor.trim().trimEnd('/')).apply()
        }

    var alunoId: Int
        get() = prefs.getInt("aluno_id", 0)
        set(valor) {
            prefs.edit().putInt("aluno_id", valor).apply()
        }

    var alunoNome: String
        get() = prefs.getString("aluno_nome", "") ?: ""
        set(valor) {
            prefs.edit().putString("aluno_nome", valor).apply()
        }

    var alunoTurma: String
        get() = prefs.getString("aluno_turma", "") ?: ""
        set(valor) {
            prefs.edit().putString("aluno_turma", valor).apply()
        }

    var alunoCodigo: String
        get() = prefs.getString("aluno_codigo", "") ?: ""
        set(valor) {
            prefs.edit().putString("aluno_codigo", valor).apply()
        }

    val temServidor: Boolean get() = servidor.isNotBlank()
    val temAluno: Boolean get() = alunoId > 0

    fun guardarAluno(aluno: Aluno) {
        alunoId = aluno.id
        alunoNome = aluno.nome
        alunoTurma = aluno.turma
        alunoCodigo = aluno.codigo
    }

    fun esquecerAluno() {
        prefs.edit()
            .remove("aluno_id")
            .remove("aluno_nome")
            .remove("aluno_turma")
            .remove("aluno_codigo")
            .apply()
    }
}
