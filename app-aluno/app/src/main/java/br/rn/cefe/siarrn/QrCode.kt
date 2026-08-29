package br.rn.cefe.siarrn

import android.graphics.Bitmap
import android.graphics.Color
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel

/**
 * Desenha o QR do aluno.
 *
 * Os dois parâmetros abaixo vieram de medição do lado do totem, e precisam ser
 * os mesmos aqui: quem lê o código da tela do celular é a mesma câmera que lê o
 * cartão de papel.
 *
 * **Correção de erro alta.** Um código de oito caracteres cabe na versão 1 do QR
 * mesmo no nível máximo, então a robustez não custa tamanho nenhum.
 *
 * **Margem de 4 módulos.** É a "quiet zone" exigida pelo padrão. Com menos, a
 * leitura falhava com o código inclinado ou distante — e ninguém segura o
 * celular reto na fila do almoço.
 */
private const val MARGEM_EM_MODULOS = 4

fun gerarQr(conteudo: String, lado: Int): Bitmap? {
    if (conteudo.isBlank() || lado <= 0) return null

    return try {
        val dicas = mapOf(
            EncodeHintType.ERROR_CORRECTION to ErrorCorrectionLevel.H,
            EncodeHintType.MARGIN to MARGEM_EM_MODULOS,
            EncodeHintType.CHARACTER_SET to "UTF-8",
        )
        val matriz = QRCodeWriter().encode(conteudo, BarcodeFormat.QR_CODE, lado, lado, dicas)

        val pixels = IntArray(lado * lado)
        for (y in 0 until lado) {
            val linha = y * lado
            for (x in 0 until lado) {
                pixels[linha + x] = if (matriz.get(x, y)) Color.BLACK else Color.WHITE
            }
        }

        Bitmap.createBitmap(lado, lado, Bitmap.Config.ARGB_8888).apply {
            setPixels(pixels, 0, lado, 0, 0, lado, lado)
        }
    } catch (erro: Exception) {
        // Um QR que não desenha não pode derrubar a tela: o aluno ainda tem o
        // próprio nome para procurar no totem.
        null
    }
}
