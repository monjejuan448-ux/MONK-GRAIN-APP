package co.monkgrain.movil.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import co.monkgrain.movil.data.CatalogRepository
import co.monkgrain.movil.data.dto.LotDetailDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** El estado de la pantalla de detalle. Mismo patrón que la lista. */
class LotDetailViewModel(
    private val repositorio: CatalogRepository = CatalogRepository(),
) : ViewModel() {

    data class Estado(
        val cargando: Boolean = true,
        val lote: LotDetailDto? = null,
        val error: String? = null,
    )

    private val _estado = MutableStateFlow(Estado())
    val estado: StateFlow<Estado> = _estado.asStateFlow()

    /**
     * No se carga en `init` como en la lista: aquí hace falta el `slug`, que
     * llega en el intent, y el ViewModel se crea antes de poder leerlo.
     */
    fun cargar(slug: String) {
        _estado.value = Estado(cargando = true)
        viewModelScope.launch {
            _estado.value = when (val r = repositorio.lote(slug)) {
                is CatalogRepository.Resultado.Exito ->
                    Estado(cargando = false, lote = r.dato)
                is CatalogRepository.Resultado.Fallo ->
                    Estado(cargando = false, error = r.mensaje)
            }
        }
    }
}
