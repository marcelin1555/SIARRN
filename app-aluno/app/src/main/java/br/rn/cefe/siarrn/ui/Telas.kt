package br.rn.cefe.siarrn.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.rn.cefe.siarrn.Ambar
import br.rn.cefe.siarrn.Aluno
import br.rn.cefe.siarrn.AlmocoViewModel
import br.rn.cefe.siarrn.Azul
import br.rn.cefe.siarrn.AzulEscuro
import br.rn.cefe.siarrn.Fundo
import br.rn.cefe.siarrn.Laranja
import br.rn.cefe.siarrn.TintaSuave
import br.rn.cefe.siarrn.Verde
import br.rn.cefe.siarrn.gerarQr

/** Faixa azul no topo, a mesma assinatura do SIGBEF e do totem. */
@Composable
fun Cabecalho(titulo: String, subtitulo: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(AzulEscuro)
            .padding(24.dp, 28.dp, 24.dp, 24.dp)
    ) {
        Text(titulo, color = androidx.compose.ui.graphics.Color.White,
            fontSize = 26.sp, fontWeight = FontWeight.Bold)
        if (subtitulo.isNotBlank()) {
            Spacer(Modifier.height(4.dp))
            Text(subtitulo, color = androidx.compose.ui.graphics.Color(0xFFCFE2F8), fontSize = 15.sp)
        }
    }
}

@Composable
private fun Recado(texto: String) {
    if (texto.isBlank()) return
    Card(
        Modifier.fillMaxWidth().padding(top = 16.dp),
        colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color(0xFFFFF3E6)),
    ) {
        Text(texto, Modifier.padding(16.dp), color = Laranja, fontSize = 14.sp)
    }
}

// ---------------------------------------------------------------------------
// 1. Onde fica o servidor
// ---------------------------------------------------------------------------
@Composable
fun TelaServidor(modelo: AlmocoViewModel) {
    var endereco by remember { mutableStateOf("192.168.") }

    Column(Modifier.fillMaxSize().background(Fundo)) {
        Cabecalho("SIARRN", "Sistema Integrado de Almoço e Refeição")

        Column(Modifier.padding(24.dp)) {
            Text("Endereço do sistema", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(
                "A escola informa esse número — costuma estar num cartaz perto do " +
                    "refeitório. Você só precisa digitar uma vez.",
                fontSize = 14.sp, color = TintaSuave,
            )

            Spacer(Modifier.height(20.dp))
            OutlinedTextField(
                value = endereco,
                onValueChange = { endereco = it },
                label = { Text("exemplo: 192.168.0.10:8770") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(Modifier.height(20.dp))
            Button(
                onClick = { modelo.definirServidor(endereco) },
                enabled = !modelo.carregando && endereco.length > 8,
                modifier = Modifier.fillMaxWidth().height(54.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Verde),
            ) {
                if (modelo.carregando) {
                    CircularProgressIndicator(
                        Modifier.size(22.dp),
                        color = androidx.compose.ui.graphics.Color.White,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text("Conectar", fontSize = 17.sp, fontWeight = FontWeight.Bold)
                }
            }

            Recado(modelo.recado)
        }
    }
}

// ---------------------------------------------------------------------------
// 2. Quem é o dono do aparelho
// ---------------------------------------------------------------------------
@Composable
fun TelaEscolherAluno(modelo: AlmocoViewModel) {
    var termo by remember { mutableStateOf("") }
    var cadastrando by remember { mutableStateOf(false) }
    var nomeNovo by remember { mutableStateOf("") }
    var turmaNova by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().background(Fundo)) {
        Cabecalho("Quem é você?", "Só na primeira vez. Depois o app já sabe.")

        Column(Modifier.padding(24.dp).verticalScroll(rememberScrollState())) {
            if (!cadastrando) {
                OutlinedTextField(
                    value = termo,
                    onValueChange = {
                        termo = it
                        modelo.buscar(it)
                    },
                    label = { Text("primeiras letras do seu nome") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )

                Spacer(Modifier.height(12.dp))
                modelo.encontrados.forEach { aluno -> LinhaAluno(aluno) { modelo.escolher(aluno) } }

                if (termo.length >= 2 && modelo.encontrados.isEmpty()) {
                    Spacer(Modifier.height(16.dp))
                    Text("Nenhum nome encontrado.", color = TintaSuave, fontSize = 14.sp)
                    TextButton(onClick = { cadastrando = true; nomeNovo = termo }) {
                        Text("Não estou na lista — quero me cadastrar")
                    }
                }
            } else {
                Text("Cadastro", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = nomeNovo, onValueChange = { nomeNovo = it },
                    label = { Text("nome completo") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = turmaNova, onValueChange = { turmaNova = it },
                    label = { Text("turma") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(16.dp))
                Row {
                    Button(
                        onClick = { modelo.cadastrar(nomeNovo, turmaNova) },
                        enabled = !modelo.carregando && nomeNovo.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = Verde),
                    ) { Text("Cadastrar") }
                    Spacer(Modifier.width(10.dp))
                    OutlinedButton(onClick = { cadastrando = false }) { Text("Voltar") }
                }
            }

            Recado(modelo.recado)
        }
    }
}

@Composable
private fun LinhaAluno(aluno: Aluno, aoTocar: () -> Unit) {
    Card(
        Modifier.fillMaxWidth().padding(bottom = 8.dp).clickable(onClick = aoTocar),
        colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.White),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(18.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(aluno.nome, fontSize = 17.sp, fontWeight = FontWeight.Medium)
            Text(aluno.turma, fontSize = 14.sp, color = TintaSuave)
        }
    }
}

// ---------------------------------------------------------------------------
// 3. O dia: cardápio, declaração e o QR
// ---------------------------------------------------------------------------
@Composable
fun TelaHoje(modelo: AlmocoViewModel) {
    val hoje = modelo.hoje

    Column(
        Modifier.fillMaxSize().background(Fundo).verticalScroll(rememberScrollState())
    ) {
        Cabecalho(modelo.nome.ifBlank { "SIARRN" }, modelo.turma)

        Column(Modifier.padding(20.dp)) {
            // O QR vem primeiro de propósito: é o que resolve a fila, e é a
            // única parte da tela que funciona sem conexão nenhuma.
            CartaoDoQr(modelo.codigo)

            Spacer(Modifier.height(20.dp))
            CartaoDoCardapio(hoje?.cardapio ?: "")

            Spacer(Modifier.height(20.dp))
            if (hoje?.jaAlmocou == true) {
                Card(
                    Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Verde),
                ) {
                    Text(
                        "Você já almoçou hoje. Bom proveito!",
                        Modifier.fillMaxWidth().padding(20.dp),
                        color = androidx.compose.ui.graphics.Color.White,
                        fontSize = 17.sp, fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                    )
                }
            } else {
                Declaracao(modelo, hoje?.declarou)
            }

            Recado(modelo.recado)

            Spacer(Modifier.height(28.dp))
            HorizontalDivider()
            TextButton(onClick = { modelo.trocarDeAluno() }) {
                Text("Este celular não é meu", color = TintaSuave, fontSize = 13.sp)
            }
        }
    }
}

@Composable
private fun CartaoDoQr(codigo: String) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.White),
    ) {
        Column(
            Modifier.fillMaxWidth().padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("MOSTRE NA FILA", fontSize = 12.sp, color = Azul, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(14.dp))

            val bitmap = remember(codigo) { gerarQr(codigo, 520) }
            if (bitmap != null) {
                Image(bitmap.asImageBitmap(), contentDescription = "Código do aluno",
                    modifier = Modifier.size(230.dp))
            } else {
                Box(Modifier.size(230.dp).background(Fundo))
            }

            Spacer(Modifier.height(12.dp))
            Text(codigo, fontSize = 16.sp, color = TintaSuave, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun CartaoDoCardapio(cardapio: String) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.White),
    ) {
        Column(Modifier.fillMaxWidth()) {
            Box(Modifier.fillMaxWidth().height(5.dp).background(Ambar))
            Column(Modifier.padding(20.dp)) {
                Text("HOJE NO ALMOÇO", fontSize = 12.sp, color = AzulEscuro,
                    fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                Text(
                    cardapio.ifBlank { "A cozinha ainda não informou o cardápio." },
                    fontSize = if (cardapio.isBlank()) 15.sp else 20.sp,
                    color = if (cardapio.isBlank()) TintaSuave else androidx.compose.ui.graphics.Color(0xFF1A1A1A),
                )
            }
        }
    }
}

@Composable
private fun Declaracao(modelo: AlmocoViewModel, declarou: Boolean?) {
    Text(
        when (declarou) {
            true -> "Você avisou que vem almoçar."
            false -> "Você avisou que não vem hoje."
            // Silêncio não é recusa: a cozinha conta essa pessoa pelo hábito
            // dela, e o texto precisa deixar claro que avisar é um favor, não
            // uma obrigação.
            null -> "Avisar ajuda a cozinha a preparar a quantidade certa."
        },
        fontSize = 15.sp,
        color = TintaSuave,
    )

    Spacer(Modifier.height(12.dp))
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(
            onClick = { modelo.declarar(true) },
            enabled = !modelo.carregando,
            modifier = Modifier.weight(1f).height(58.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (declarou == true) Verde else androidx.compose.ui.graphics.Color.White,
                contentColor = if (declarou == true) androidx.compose.ui.graphics.Color.White else Verde,
            ),
        ) { Text("Vou almoçar", fontWeight = FontWeight.Bold) }

        Button(
            onClick = { modelo.declarar(false) },
            enabled = !modelo.carregando,
            modifier = Modifier.weight(1f).height(58.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (declarou == false) Laranja else androidx.compose.ui.graphics.Color.White,
                contentColor = if (declarou == false) androidx.compose.ui.graphics.Color.White else Laranja,
            ),
        ) { Text("Hoje não vou", fontWeight = FontWeight.Bold) }
    }
}
