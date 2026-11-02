package co.monkgrain.movil.data

import co.monkgrain.movil.data.dto.LotDetailDto
import co.monkgrain.movil.data.dto.LotListItemDto
import co.monkgrain.movil.data.dto.PageDto
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * El contrato con la API del catálogo.
 *
 * Es una interfaz y no una clase: Retrofit genera la implementación. Eso deja
 * la definición al lado de lo que importa —ruta, método y parámetros— y
 * permite sustituirla por una falsa en una prueba sin tocar nada más.
 *
 * Son `suspend`: la llamada de red **no puede ocurrir en el hilo principal**
 * —Android lanza `NetworkOnMainThreadException` si se intenta— y una función
 * de suspensión lo resuelve sin callbacks anidados.
 */
interface CatalogApi {

    /**
     * La lista de lotes, paginada.
     *
     * `maxYieldFactor` es `max` y no `min`, y ahí está el dominio entero:
     * en el factor de rendimiento **menos es mejor**, así que acotar por
     * arriba es pedir café igual o mejor que ese número.
     */
    @GET("products")
    suspend fun lotes(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("q") busqueda: String? = null,
        @Query("max_yield_factor") maxYieldFactor: String? = null,
    ): PageDto<LotListItemDto>

    /**
     * El detalle de un lote.
     *
     * Se busca por `slug` y no por identificador porque es lo que la API
     * expone: el slug es legible y estable, y sirve para compartir un enlace.
     */
    @GET("products/{slug}")
    suspend fun lote(@Path("slug") slug: String): LotDetailDto
}
