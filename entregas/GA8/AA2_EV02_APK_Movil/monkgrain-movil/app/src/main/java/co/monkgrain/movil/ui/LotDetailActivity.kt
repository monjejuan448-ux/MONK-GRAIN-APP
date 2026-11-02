package co.monkgrain.movil.ui

import android.os.Bundle
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import co.monkgrain.movil.R
import co.monkgrain.movil.databinding.ActivityLotDetailBinding
import co.monkgrain.movil.domain.Kilos
import co.monkgrain.movil.domain.Money
import co.monkgrain.movil.domain.YieldFactor
import kotlinx.coroutines.launch

/** El detalle de un lote. */
class LotDetailActivity : AppCompatActivity() {

    private lateinit var vista: ActivityLotDetailBinding
    private val modelo: LotDetailViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vista = ActivityLotDetailBinding.inflate(layoutInflater)
        setContentView(vista.root)

        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        // El slug llega en el intent. Si no viene —no debería, pero un
        // intent se puede construir desde fuera— se cierra en vez de
        // reventar con un NullPointerException.
        val slug = intent.getStringExtra(EXTRA_SLUG)
        if (slug.isNullOrBlank()) {
            finish()
            return
        }

        // Solo la primera vez: al girar la pantalla, el ViewModel ya tiene el
        // lote y volver a pedirlo sería una petición de red regalada.
        if (savedInstanceState == null) {
            modelo.cargar(slug)
        }

        observarEstado()
    }

    private fun observarEstado() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                modelo.estado.collect { estado ->
                    vista.cargando.visibility = visible(estado.cargando)
                    vista.error.visibility = visible(estado.error != null)
                    vista.error.text = estado.error

                    val lote = estado.lote ?: return@collect
                    vista.contenido.visibility = android.view.View.VISIBLE

                    title = lote.name
                    vista.nombre.text = lote.name
                    vista.descripcion.text = lote.description
                    vista.vendedor.text =
                        lote.producer.brandName ?: lote.producer.legalName

                    vista.factor.text =
                        YieldFactor.texto(YieldFactor.desdeTexto(lote.yieldFactor))
                    vista.humedad.text = lote.moisturePct?.let { "Humedad $it %" }
                        ?: "Humedad sin declarar"

                    vista.precio.text = Money.porKilo(Money.desdeTexto(lote.basePrice))
                    vista.disponible.text = Kilos.texto(lote.availableKg)

                    // El mínimo de despacho vive en la variante, no en el
                    // lote: cada presentación tiene el suyo. Se muestra el
                    // menor, que es desde cuánto se puede comprar.
                    val minimo = lote.variants.filter { it.isActive }
                        .minOfOrNull { it.minQtyKg }
                    vista.minimo.text = minimo
                        ?.let { getString(R.string.minimo_desde, Kilos.texto(it)) }
                        ?: getString(R.string.sin_presentaciones)

                    vista.despacho.text =
                        resources.getQuantityString(
                            R.plurals.despacho_dias,
                            lote.dispatchDays,
                            lote.dispatchDays,
                        )
                }
            }
        }
    }

    private fun visible(condicion: Boolean) =
        if (condicion) android.view.View.VISIBLE else android.view.View.GONE

    companion object {
        const val EXTRA_SLUG = "co.monkgrain.movil.SLUG"
    }
}
