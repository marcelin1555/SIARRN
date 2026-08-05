// SIARRN — Totem e painel da cozinha (JavaFX)
//
// Um programa, dois modos. O totem fica em tela cheia na fila do almoço; o modo
// gestão, atrás de um PIN, é o painel da cozinha. A escola instala o mesmo
// binário onde precisar — em duas máquinas, se tiver duas; alternando na mesma,
// se só houver uma.

plugins {
    application
    id("org.openjfx.javafxplugin") version "0.1.0"
}

repositories {
    mavenCentral()
}

// JavaFX deixou de vir dentro do JDK na versão 11. O plugin acima resolve os
// módulos certos para o sistema operacional em que o build está rodando.
javafx {
    version = "21.0.5"
    modules = listOf("javafx.controls")
}

dependencies {
    // Único terceiro no projeto. Escrever um parser de JSON à mão seria
    // trabalho sem aprendizado nenhum.
    implementation("com.google.code.gson:gson:2.11.0")
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

application {
    mainClass = "br.siarrn.totem.App"
}

tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
    options.compilerArgs.add("-Xlint:all")
}

// Verificação sem abrir a interface: confere se esta máquina enxerga o servidor
// e exercita a fila offline. Usada tanto no desenvolvimento quanto na escola,
// antes de a fila do almoço se formar.
tasks.register<JavaExec>("verificar") {
    group = "verification"
    description = "Testa conexão com o servidor, busca local e fila offline."
    mainClass = "br.siarrn.totem.Diagnostico"
    classpath = sourceSets["main"].runtimeClasspath
    // Sem isto, os acentos da saída saem como interrogação no console do Windows.
    jvmArgs("-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8")
}
