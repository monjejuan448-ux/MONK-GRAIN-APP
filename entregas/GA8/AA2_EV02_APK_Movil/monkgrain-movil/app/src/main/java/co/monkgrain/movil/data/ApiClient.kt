package co.monkgrain.movil.data

import co.monkgrain.movil.BuildConfig
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit

/**
 * Construye el cliente HTTP.
 *
 * ## La dirección del servidor
 *
 * No está escrita aquí: viene de `BuildConfig.API_BASE_URL`, que
 * `build.gradle.kts` define distinto en `debug` y en `release`. El motivo es
 * concreto y cuesta una tarde descubrirlo:
 *
 * **El emulador no llega a `localhost`.** El emulador es una máquina virtual
 * con su propia red, así que `localhost` dentro de él es *el emulador
 * mismo*, no el equipo donde corre `docker compose`. La dirección del
 * anfitrión, vista desde el emulador, es **`10.0.2.2`**.
 *
 * Con un teléfono real conectado por USB hay dos caminos: usar la IP del
 * equipo en la red local, o `adb reverse tcp:8000 tcp:8000`, que reenvía el
 * puerto y permite usar `localhost`.
 */
object ApiClient {

    /**
     * El lector de JSON.
     *
     * `ignoreUnknownKeys` está activado a propósito: la API devuelve campos
     * que esta aplicación no usa —certificaciones, atributos, finca— y sin
     * esto cada campo nuevo del servidor rompería la aplicación instalada.
     * Es lo que permite que el servidor evolucione sin obligar a actualizar
     * el teléfono de cada caficultor.
     *
     * `coerceInputValues` queda en `false`, que es el valor de serie, y es
     * deliberado: con él activado, un `null` donde se espera un valor se
     * convierte en silencio al valor por omisión, y un dato ausente pasaría
     * desapercibido en vez de fallar.
     */
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = false
    }

    private val cliente: OkHttpClient by lazy {
        OkHttpClient.Builder()
            // Plazos explícitos. Sin ellos, una red mala deja la pantalla
            // cargando indefinidamente y el usuario no sabe si esperar.
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    // El cuerpo completo SOLO en debug. En release ni
                    // siquiera las cabeceras: ahí viajarían los tokens, y
                    // quedarían escritos en el registro del dispositivo.
                    level = if (BuildConfig.DEBUG) {
                        HttpLoggingInterceptor.Level.BODY
                    } else {
                        HttpLoggingInterceptor.Level.NONE
                    }
                },
            )
            .build()
    }

    val catalogo: CatalogApi by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(cliente)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(CatalogApi::class.java)
    }
}
