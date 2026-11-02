package co.monkgrain.movil.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.monkgrain.movil.data.CatalogRepository
import co.monkgrain.movil.data.dto.LotListItemDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * El estado de la pantalla de lotes.
 *
 * **Por qué un ViewModel y no una variable en la Activity.** El sistema
 * destruye y vuelve a crear la Activity cuando el usuario gira el teléfono.
 * Con el estado en la Activity, girar borra la lista y dispara otra petición;
 * con el ViewModel, el estado sobrevive y la red no se vuelve a tocar.
 *
 * Es el mismo problema que resolvía `useProtectedResource` en el frontend
 * web, con otro nombre: separar el estado de la pantalla de la pantalla.
 */
class LotListViewModel(
    private val repositorio: CatalogRepository = CatalogRepository(),
) : ViewModel() {

    /**
     * Los cuatro estados son **separados y no uno combinado**, porque no son
     * intercambiables: *cargando* no sabe nada todavía, *vacío* sí sabe y no
     * hay nada que mostrar, y *error* ofrece reintentar. Un solo campo con
     * un enum obligaría a inventar combinaciones imposibles.
     */
    data class Estado(
        val cargando: Boolean = true,
        val lotes: List<LotListItemDto> = emptyList(),
        val error: String? = null,
        val sinConexion: Boolean = false,
    )

    private val _estado = MutableStateFlow(Estado())
    val estado: StateFlow<Estado> = _estado.asStateFlow()

    init {
        cargar()
    }

    /**
     * Pide la lista.
     *
     * `viewModelScope` cancela la corrutina si el ViewModel desaparece. Sin
     * eso, una respuesta que llega tarde intentaría escribir sobre una
     * pantalla que ya no existe.
     */
    fun cargar(maxYieldFactor: String? = null) {
        _estado.value = Estado(cargando = true)
        viewModelScope.launch {
            _estado.value = when (val r = repositorio.lotes(maxYieldFactor = maxYieldFactor)) {
                is CatalogRepository.Resultado.Exito ->
                    Estado(cargando = false, lotes = r.dato)
                is CatalogRepository.Resultado.Fallo ->
                    Estado(cargando = false, error = r.mensaje, sinConexion = r.sinConexion)
            }
        }
    }
}
