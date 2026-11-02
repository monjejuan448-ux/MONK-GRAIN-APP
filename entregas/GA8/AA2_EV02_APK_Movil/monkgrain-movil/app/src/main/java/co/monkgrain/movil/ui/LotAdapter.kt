package co.monkgrain.movil.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import co.monkgrain.movil.data.dto.LotListItemDto
import co.monkgrain.movil.databinding.ItemLotBinding
import co.monkgrain.movil.domain.Kilos
import co.monkgrain.movil.domain.Money
import co.monkgrain.movil.domain.YieldFactor

/**
 * Dibuja cada lote de la lista.
 *
 * `ListAdapter` y no `RecyclerView.Adapter` a secas: calcula por su cuenta
 * qué filas cambiaron y anima solo esas, en lugar de volver a dibujar la
 * lista entera con `notifyDataSetChanged()`.
 *
 * Esta clase es el **componente reutilizable** de la capa de presentación: la
 * misma fila sirve para el catálogo y serviría para «mis lotes» en el panel
 * del vendedor, cambiando únicamente lo que ocurre al tocarla.
 */
class LotAdapter(
    private val alTocar: (LotListItemDto) -> Unit,
) : ListAdapter<LotListItemDto, LotAdapter.Fila>(COMPARADOR) {

    inner class Fila(private val vista: ItemLotBinding) :
        RecyclerView.ViewHolder(vista.root) {

        fun pintar(lote: LotListItemDto) {
            vista.nombre.text = lote.name
            vista.vendedor.text = lote.producer.brandName ?: lote.producer.legalName

            // El origen puede faltar entero. Se arma con lo que haya, y si no
            // hay nada se dice, porque un renglón vacío parece un fallo.
            vista.origen.text = listOfNotNull(lote.municipality, lote.department)
                .joinToString(", ")
                .ifBlank { "Origen sin declarar" }

            // El factor NUNCA sale como número solo: sin su lectura, un
            // «88.50» no le dice nada a quien no sabe que el estándar es 94.
            vista.factor.text = YieldFactor.texto(YieldFactor.desdeTexto(lote.yieldFactor))

            vista.precio.text = Money.porKilo(Money.desdeTexto(lote.basePrice))
            vista.disponible.text = Kilos.texto(lote.availableKg)

            vista.root.setOnClickListener { alTocar(lote) }
        }
    }

    override fun onCreateViewHolder(padre: ViewGroup, tipo: Int): Fila =
        Fila(ItemLotBinding.inflate(LayoutInflater.from(padre.context), padre, false))

    override fun onBindViewHolder(fila: Fila, posicion: Int) = fila.pintar(getItem(posicion))

    private companion object {
        /**
         * Cómo se compara una fila con otra.
         *
         * `areItemsTheSame` pregunta si son el MISMO lote —por su
         * identificador— y `areContentsTheSame` si además muestran lo mismo.
         * Confundirlos hace que la lista parpadee entera en cada
         * actualización.
         */
        val COMPARADOR = object : DiffUtil.ItemCallback<LotListItemDto>() {
            override fun areItemsTheSame(a: LotListItemDto, b: LotListItemDto) = a.id == b.id
            override fun areContentsTheSame(a: LotListItemDto, b: LotListItemDto) = a == b
        }
    }
}
