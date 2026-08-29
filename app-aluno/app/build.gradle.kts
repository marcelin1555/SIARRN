plugins {
    // O AGP 9 já aplica o plugin Kotlin. Declarar `kotlin.android` aqui faz o
    // build falhar com "extension already registered with that name" — é por
    // isso que o sigbef-mobile também não o declara.
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "br.rn.cefe.siarrn"
    compileSdk = 36

    defaultConfig {
        applicationId = "br.rn.cefe.siarrn"
        // Android 7. Cobre praticamente qualquer aparelho que um aluno de
        // escola pública ainda use — inclusive os de cinco ou seis anos atrás.
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
    }

    signingConfigs {
        // A chave fica fora do repositório: chave privada não se versiona. O
        // caminho e as senhas podem vir do ambiente, para o dia em que o build
        // rodar em outra máquina.
        //
        // Sem a chave, o `assembleRelease` ainda funciona e gera um APK não
        // assinado — que compila, mas não instala. Quem for distribuir precisa
        // da chave; ver o LEIA-ME desta pasta.
        val caminhoChave = System.getenv("SIARRN_KEYSTORE") ?: "${rootDir}/siarrn-release.jks"
        if (file(caminhoChave).exists()) {
            create("release") {
                storeFile = file(caminhoChave)
                storePassword = System.getenv("SIARRN_STORE_PASSWORD") ?: "siarrn2026"
                keyAlias = System.getenv("SIARRN_KEY_ALIAS") ?: "siarrn"
                keyPassword = System.getenv("SIARRN_KEY_PASSWORD") ?: "siarrn2026"
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.findByName("release")
            // O APK é distribuído pela rede da escola, não por loja: quanto
            // menor, menos gente desiste no aviso de "fontes desconhecidas".
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures { compose = true }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    debugImplementation(libs.androidx.ui.tooling)

    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.zxing.core)

    testImplementation(libs.junit)
}
