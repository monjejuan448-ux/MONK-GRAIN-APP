package co.monkgrain.movil.data

import co.monkgrain.movil.data.dto.LotDetailDto
import co.monkgrain.movil.data.dto.LotListItemDto
import java.io.IOException
import retrofit2.HttpException

/**
 * La única puerta a los datos del catálogo.
 *
 * Existe para que el `ViewModel` no sepa que detrás hay Retrofit. Si mañana
 * se añade una caché local, o se cambia de biblioteca, el cambio queda
 * encerrado aquí.
 *
 * Y hace algo más importante: **traduce los fallos**. Una excepción de red no
 * debe llegar a la pantalla, porque «UnknownHostException» no le dice nada a
 * un caficultor. Lo que sube es un [Resultado] con un mensaje que se puede
 * mostrar.
 */
class CatalogRepository(private val api: CatalogApi = ApiClient.catalogo) {

    /**
     * Lo que devuelve cada operación.
     *
     * Una clase sellada y no una excepción: obliga a quien llama a tratar el
     * caso de error, porque el compilador exige cubrir las dos ramas. Con
     * excepciones, olvidar el `catch` compila sin protestar.
     */
    sealed interface Resultado<out T> {
        data class Exito<T>(val dato: T) : Resultado<T>
        data class Fallo(val mensaje: String, val sinConexion: Boolean) : Resultado<Nothing>
    }

    suspend fun lotes(pagina: Int = 1, maxYieldFactor: String? = null):
        Resultado<List<LotListItemDto>> = envolver {
        api.lotes(page = pagina, maxYieldFactor = maxYieldFactor).items
    }

    suspend fun lote(slug: String): Resultado<LotDetailDto> = envolver {
        api.lote(slug)
    }

    /**
     * Ejecuta la llamada y convierte lo que falle en un mensaje.
     *
     * Se distingue la falta de conexión del resto porque la acción que
     * corresponde es distinta: sin conexión, reintentar tiene sentido; ante
     * un 500, no.
     */
    private suspend fun <T> envolver(llamada: suspend () -> T): Resultado<T> =
        try {
            Resultado.Exito(llamada())
        } catch (sinRed: IOException) {
            Resultado.Fallo(
                "No pudimos conectarnos. Revisa tu conexión e inténtalo de nuevo.",
                sinConexion = true,
            )
        } catch (respuestaMala: HttpException) {
            Resultado.Fallo(mensajeDe(respuestaMala.code()), sinConexion = false)
        }

    private fun mensajeDe(codigo: Int): String = when (codigo) {
        404 -> "No encontramos este lote."
        in 500..599 -> "El servidor tuvo un problema. Inténtalo más tarde."
        else -> "No pudimos traer la información (error $codigo)."
    }
}
