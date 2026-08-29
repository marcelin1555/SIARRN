package br.rn.cefe.siarrn

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * As cores são as mesmas do SIGBEF e do totem, copiadas de `siarrn/ui_tema.py`.
 *
 * O aluno vai usar este app e o totem no mesmo almoço, e a escola apresenta os
 * dois sistemas juntos. Parecerem da mesma família vale mais do que o app ter
 * identidade própria.
 *
 * O tema é claro e fixo: nada de cor dinâmica do Android 12. Ela deixaria o app
 * diferente em cada aparelho, e a única coisa que a identidade da escola não
 * pode ser é imprevisível.
 */
val AzulEscuro = Color(0xFF1F4E79)
val Azul = Color(0xFF2E75B6)
val Ambar = Color(0xFFF2A900)
val Verde = Color(0xFF2E7D32)
val Laranja = Color(0xFFEF6C00)
val Fundo = Color(0xFFF5F7FA)
val Tinta = Color(0xFF1A1A1A)
val TintaSuave = Color(0xFF5B6B7A)
val Borda = Color(0xFFD5DAE0)

private val Cores = lightColorScheme(
    primary = AzulEscuro,
    onPrimary = Color.White,
    secondary = Azul,
    onSecondary = Color.White,
    tertiary = Ambar,
    background = Fundo,
    onBackground = Tinta,
    surface = Color.White,
    onSurface = Tinta,
    surfaceVariant = Color.White,
    onSurfaceVariant = TintaSuave,
    outline = Borda,
    error = Laranja,
)

@Composable
fun TemaSiarrn(conteudo: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Cores, content = conteudo)
}
