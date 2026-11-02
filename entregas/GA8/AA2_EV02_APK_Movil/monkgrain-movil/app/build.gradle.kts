plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "co.monkgrain.movil"
    compileSdk = 34

    defaultConfig {
        applicationId = "co.monkgrain.movil"

        // 24 (Android 7.0) cubre mas del 95 % de los dispositivos en uso.
        // Bajarlo mas obligaria a comprobar en tiempo de ejecucion si cada
        // funcion existe, por un puñado de usuarios.
        minSdk = 24
        targetSdk = 34

        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            // La direccion de la API se inyecta como campo del BuildConfig y
            // no se escribe en el codigo: el emulador y un telefono real no
            // llegan al servidor por la misma direccion. Ver ApiClient.
            buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000/api/v1/\"")
            isMinifyEnabled = false
        }
        release {
            buildConfigField("String", "API_BASE_URL", "\"https://api.monkgrain.co/api/v1/\"")

            // Ofuscacion y reduccion de codigo. Las reglas de proguard
            // conservan los DTO, que se leen por reflexion.
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")

    // ViewModel: el estado sobrevive al giro de pantalla, que destruye y
    // vuelve a crear la Activity.
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.4")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.activity:activity-ktx:1.9.1")

    // Retrofit con kotlinx.serialization. Serialization y no Gson porque
    // trabaja con los tipos de Kotlin: un campo declarado no nulo que llega
    // nulo en el JSON falla al leerlo, en vez de dejar un null dentro de una
    // variable que el compilador cree segura.
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:1.0.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Pruebas de las reglas del dominio: corren en la JVM, sin dispositivo
    // ni emulador, porque las reglas no dependen de Android.
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.24")
}
