package co.monkgrain.movil.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Los objetos que llegan de la API del catálogo.
 *
 * **Los nombres de campo son los del JSON**, en `snake_case`, declarados con
 * `@SerialName` para no renombrarlos a mano. Equivocarse en uno es el error
 * más común de un cliente móvil y el más difícil de ver: compila sin
 * problema y falla solo al recibir la respuesta.
 *
 * Por eso este archivo se verifica contra el documento OpenAPI del servicio
 * en marcha, con `verificar_contrato.py`. El contrato se comprueba, no se
 * recuerda.
 *
 * `BigDecimal` no se usa aquí sino en el dominio: el dinero y el factor de
 * rendimiento llegan como **texto** —la API los envía así para no perder
 * precisión— y se convierten al cruzar al dominio, donde `Money` y
 * `YieldFactor` saben qué hacer si el texto no es un número.
 */

/** La envoltura de página, igual en todas las listas de la API. */
@Serializable
data class PageDto<T>(
    val items: List<T>,
    val total: Int,
    val page: Int,
    @SerialName("page_size") val pageSize: Int,
    @SerialName("total_pages") val totalPages: Int,
    @SerialName("has_next") val hasNext: Boolean,
    @SerialName("has_previous") val hasPrevious: Boolean,
)

/** El vendedor, resumido. */
@Serializable
data class ProducerSummaryDto(
    val id: String,
    @SerialName("legal_name") val legalName: String,
    @SerialName("brand_name") val brandName: String? = null,
    val type: String? = null,
    @SerialName("rating_avg") val ratingAvg: String? = null,
)

/**
 * Un lote en la lista.
 *
 * Los campos que la API declara `string | null` se escriben con `?` en
 * Kotlin. No es un detalle de estilo: con `kotlinx.serialization`, un campo
 * declarado no nulo que llega nulo **falla al leer el JSON**, y ese fallo es
 * preferible a un `null` dentro de una variable que el compilador cree
 * segura y que tumba la pantalla tres capas más abajo.
 */
@Serializable
data class LotListItemDto(
    val id: String,
    val slug: String,
    val name: String,
    val state: String,
    @SerialName("base_price") val basePrice: String,
    val currency: String,
    @SerialName("primary_image_url") val primaryImageUrl: String? = null,
    val producer: ProducerSummaryDto,
    val region: String? = null,
    val municipality: String? = null,
    val department: String? = null,
    @SerialName("yield_factor") val yieldFactor: String? = null,
    @SerialName("moisture_pct") val moisturePct: String? = null,
    @SerialName("available_kg") val availableKg: Int,
    @SerialName("rating_avg") val ratingAvg: String,
    @SerialName("rating_count") val ratingCount: Int,
    @SerialName("is_available") val isAvailable: Boolean,
)

/** Una presentación del lote, con su mínimo de despacho. */
@Serializable
data class VariantDto(
    val id: String,
    val sku: String,
    val presentation: String,
    @SerialName("min_qty_kg") val minQtyKg: Int,
    val price: String,
    @SerialName("wholesale_price") val wholesalePrice: String? = null,
    @SerialName("available_qty") val availableQty: Int,
    @SerialName("is_active") val isActive: Boolean,
)

/**
 * El detalle de un lote.
 *
 * Repite los campos de la lista y añade los suyos. Se declaran de nuevo en
 * lugar de heredar porque `data class` no hereda de `data class` en Kotlin, y
 * forzarlo con una interfaz añadiría una capa que no paga lo que cuesta para
 * dos objetos.
 *
 * Los campos anidados que esta aplicación no usa —`attributes`, `farm`,
 * `category`, `certifications`— se omiten a propósito. `ignoreUnknownKeys`
 * en el lector hace que sobren sin estorbar, y declararlos obligaría a
 * mantener seis objetos más por nada.
 */
@Serializable
data class LotDetailDto(
    val id: String,
    val slug: String,
    val name: String,
    val state: String,
    val description: String,
    @SerialName("base_price") val basePrice: String,
    val currency: String,
    @SerialName("primary_image_url") val primaryImageUrl: String? = null,
    val producer: ProducerSummaryDto,
    val region: String? = null,
    val municipality: String? = null,
    val department: String? = null,
    @SerialName("yield_factor") val yieldFactor: String? = null,
    @SerialName("moisture_pct") val moisturePct: String? = null,
    @SerialName("available_kg") val availableKg: Int,
    @SerialName("rating_avg") val ratingAvg: String,
    @SerialName("rating_count") val ratingCount: Int,
    @SerialName("is_available") val isAvailable: Boolean,
    val variants: List<VariantDto> = emptyList(),
    @SerialName("dispatch_days") val dispatchDays: Int,
    @SerialName("storage_conditions") val storageConditions: String? = null,
    @SerialName("allows_samples") val allowsSamples: Boolean,
)
