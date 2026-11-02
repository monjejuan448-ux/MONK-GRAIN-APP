package co.monkgrain.movil.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import co.monkgrain.movil.databinding.ActivityLotListBinding
import kotlinx.coroutines.launch

/**
 * La pantalla principal: el catálogo de lotes de pergamino.
 *
 * La Activity **solo dibuja**. No decide nada, no habla con la red y no sabe
 * que existe Retrofit: pide el estado al ViewModel y lo pinta. Es la misma
 * regla de dependencia del backend —`router → service → repository`— aplicada
 * a la pantalla.
 */
class LotListActivity : AppCompatActivity() {

    private lateinit var vista: ActivityLotListBinding

    // `by viewModels()` devuelve el MISMO ViewModel si la Activity se
    // recrea al girar la pantalla. Crearlo con `LotListViewModel()` daría uno
    // nuevo cada vez y perdería la lista.
    private val modelo: LotListViewModel by viewModels()

    private val adaptador = LotAdapter { lote ->
        startActivity(
            Intent(this, LotDetailActivity::class.java)
                .putExtra(LotDetailActivity.EXTRA_SLUG, lote.slug),
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vista = ActivityLotListBinding.inflate(layoutInflater)
        setContentView(vista.root)

        vista.lista.layoutManager = LinearLayoutManager(this)
        vista.lista.adapter = adaptador

        vista.reintentar.setOnClickListener { modelo.cargar() }

        observarEstado()
    }

    /**
     * Escucha el estado del ViewModel.
     *
     * `repeatOnLifecycle(STARTED)` deja de escuchar cuando la pantalla pasa a
     * segundo plano y vuelve a hacerlo al regresar. Sin esto, la aplicación
     * seguiría recibiendo actualizaciones con la pantalla apagada, gastando
     * batería por nada.
     */
    private fun observarEstado() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                modelo.estado.collect { estado ->
                    vista.cargando.visibility = visible(estado.cargando)

                    val hayError = estado.error != null
                    vista.error.visibility = visible(hayError)
                    vista.reintentar.visibility = visible(estado.sinConexion)
                    vista.error.text = estado.error

                    val vacio = !estado.cargando && !hayError && estado.lotes.isEmpty()
                    vista.vacio.visibility = visible(vacio)

                    adaptador.submitList(estado.lotes)
                }
            }
        }
    }

    private fun visible(condicion: Boolean) =
        if (condicion) android.view.View.VISIBLE else android.view.View.GONE
}
