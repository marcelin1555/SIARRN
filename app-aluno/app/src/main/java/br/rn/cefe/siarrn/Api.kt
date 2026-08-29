package br.rn.cefe.siarrn

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Um aluno, como o servidor devolve. */
data class Aluno(
    val id: Int,
    val nome: String,
    val turma: String,
    val codigo: String,
) {
    val rotulo: String get() = if (turma.isBlank()) nome else "$nome  ·  $turma"
}

/** O dia de hoje, do ponto de vista do aluno. */
data class Hoje(
    val refeicaoId: Int,
    val data: String,
    val cardapio: String,
    val declarou: Boolean?,
    val jaAlmocou: Boolean,
)

class ErroDeRede(mensagem: String) : IOException(mensagem)

/**
 * Conversa com o servidor da escola.
 *
 * `HttpURLConnection` e `org.json`, ambos da plataforma. Duas telas e meia dúzia
 * de campos não justificam Retrofit e Moshi — e cada dependência a menos é um
 * APK menor, o que importa quando a instalação passa pelo aviso de "fontes
 * desconhecidas" e cada megabyte é gente desistindo no meio.
 *
 * Os tempos limite são curtos pelo mesmo motivo do totem: o aluno está com o
 * celular na mão, provavelmente andando pelo corredor. Se a rede da escola não
 * responder em poucos segundos, é melhor dizer isso do que deixar girando.
 */
class Api(private val servidor: String) {

    private suspend fun requisitar(
        caminho: String,
        metodo: String = "GET",
        corpo: JSONObject? = null,
    ): String = withContext(Dispatchers.IO) {
        val conexao = (URL(servidor + caminho).openConnection() as HttpURLConnection).apply {
            requestMethod = metodo
            connectTimeout = 4000
            readTimeout = 6000
            setRequestProperty("Accept", "application/json")
            if (corpo != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }

        try {
            if (corpo != null) {
                conexao.outputStream.use { saida ->
                    saida.write(corpo.toString().toByteArray(Charsets.UTF_8))
                }
            }

            val codigo = conexao.responseCode
            if (codigo == 404) throw ErroDeRede("não encontrado")
            if (codigo >= 400) throw ErroDeRede("o servidor respondeu $codigo")

            conexao.inputStream.bufferedReader().use { leitor -> leitor.readText() }
        } catch (erro: IOException) {
            throw ErroDeRede(erro.message ?: "sem conexão com a escola")
        } finally {
            conexao.disconnect()
        }
    }

    /** Diz se o endereço configurado é mesmo um servidor do SIARRN. */
    suspend fun conferir(): Boolean = try {
        JSONObject(requisitar("/api/ping")).optBoolean("ok", false)
    } catch (erro: ErroDeRede) {
        false
    }

    private fun paraAluno(item: JSONObject) = Aluno(
        id = item.getInt("id"),
        nome = item.optString("nome"),
        turma = item.optString("turma"),
        codigo = item.optString("codigo"),
    )

    suspend fun buscar(termo: String): List<Aluno> {
        val consulta = URLEncoder.encode(termo, "UTF-8")
        val lista = JSONArray(requisitar("/api/alunos/busca?q=" + consulta))
        return (0 until lista.length()).map { indice -> paraAluno(lista.getJSONObject(indice)) }
    }

    suspend fun cadastrar(nome: String, turma: String): Aluno {
        val corpo = JSONObject().put("nome", nome).put("turma", turma)
        return paraAluno(JSONObject(requisitar("/api/alunos", "POST", corpo)))
    }

    /** Cardápio do dia e o que este aluno já disse — ou não disse. */
    suspend fun hoje(codigo: String): Hoje {
        val refeicao = JSONObject(requisitar("/api/refeicao/hoje"))
        val situacao = JSONObject(requisitar("/api/alunos/codigo/" + codigo))

        return Hoje(
            refeicaoId = refeicao.getInt("id"),
            data = refeicao.optString("data"),
            cardapio = if (refeicao.isNull("cardapio")) "" else refeicao.optString("cardapio"),
            // `declarou` é nulo de propósito quando ninguém disse nada: silêncio
            // não é a mesma coisa que "não vou", e a previsão trata os dois casos
            // de formas diferentes.
            declarou = if (situacao.isNull("declarou")) null else situacao.getBoolean("declarou"),
            jaAlmocou = situacao.optBoolean("ja_consumiu", false),
        )
    }

    suspend fun declarar(alunoId: Int, vai: Boolean) {
        val corpo = JSONObject().put("aluno_id", alunoId).put("vai", vai)
        requisitar("/api/declaracao", "POST", corpo)
    }
}
