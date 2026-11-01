package co.monkgrain.catalog.service;

import co.monkgrain.catalog.dao.PergaminoLotDao;
import co.monkgrain.catalog.dao.ProducerDao;
import co.monkgrain.catalog.model.PergaminoLot;
import co.monkgrain.catalog.model.Producer;
import co.monkgrain.catalog.util.ValidationException;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

/**
 * Reglas de negocio del catálogo de pergamino.
 *
 * <p>Separar el servicio del DAO no es ceremonia: el DAO sabe hablar con la
 * base de datos y el servicio sabe qué está permitido. Esa división permite
 * probar las reglas sin levantar PostgreSQL, y cambiar el motor sin tocar una
 * sola regla.
 *
 * <p>Las validaciones se repiten aquí y en la base de datos a propósito. La
 * base protege el dato venga la escritura de donde venga; el servicio produce
 * un mensaje que el usuario entiende, en lugar de un error de restricción.
 */
public class CatalogService {

    /** Fuera de este rango no existe café comercializable. */
    private static final BigDecimal MIN_YIELD_FACTOR = new BigDecimal("80");
    private static final BigDecimal MAX_YIELD_FACTOR = new BigDecimal("130");

    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100");

    private final PergaminoLotDao lotDao;
    private final ProducerDao producerDao;

    public CatalogService() {
        this(new PergaminoLotDao(), new ProducerDao());
    }

    /** Constructor con dependencias explícitas, para poder sustituirlas al probar. */
    public CatalogService(PergaminoLotDao lotDao, ProducerDao producerDao) {
        this.lotDao = lotDao;
        this.producerDao = producerDao;
    }

    // ------------------------------------------------------------------
    // Alta
    // ------------------------------------------------------------------

    /**
     * Publica un lote nuevo tras validarlo.
     *
     * @return identificador del lote registrado
     * @throws ValidationException si algún dato incumple una regla
     */
    public int registerLot(PergaminoLot lot) {
        validate(lot);

        if (producerDao.findById(lot.getProducerId()).isEmpty()) {
            throw new ValidationException(
                    "No existe el vendedor " + lot.getProducerId() + ".");
        }

        // El código identifica el lote dentro de la finca. Repetirlo haría
        // ambigua cualquier reclamación posterior.
        if (lotDao.existsLotCode(lot.getProducerId(), lot.getLotCode())) {
            throw new ValidationException(
                    "Ya tienes un lote con el código " + lot.getLotCode() + ".");
        }

        return lotDao.insert(lot);
    }

    public int registerProducer(Producer producer) {
        if (isBlank(producer.getFarmName())) {
            throw new ValidationException("El nombre de la finca es obligatorio.");
        }
        if (isBlank(producer.getMunicipality()) || isBlank(producer.getDepartment())) {
            throw new ValidationException("El municipio y el departamento son obligatorios.");
        }
        return producerDao.insert(producer);
    }

    // ------------------------------------------------------------------
    // Consulta
    // ------------------------------------------------------------------

    public List<PergaminoLot> listAll() {
        return lotDao.findAll();
    }

    public Optional<PergaminoLot> findLot(int lotId) {
        return lotDao.findById(lotId);
    }

    public List<Producer> listProducers() {
        return producerDao.findAll();
    }

    /**
     * Catálogo visible para un comprador.
     *
     * @param maxYieldFactor techo de factor aceptado, o {@code null} sin filtro
     */
    public List<PergaminoLot> browseCatalog(BigDecimal maxYieldFactor) {
        if (maxYieldFactor != null && !isWithinYieldRange(maxYieldFactor)) {
            throw new ValidationException(
                    "El factor de rendimiento debe estar entre 80 y 130.");
        }
        return lotDao.findPublished(maxYieldFactor);
    }

    // ------------------------------------------------------------------
    // Modificación
    // ------------------------------------------------------------------

    /**
     * Actualiza un lote existente.
     *
     * @throws ValidationException si el lote no existe o los datos no son válidos
     */
    public void updateLot(PergaminoLot lot) {
        validate(lot);

        if (lotDao.findById(lot.getLotId()).isEmpty()) {
            throw new ValidationException("No existe el lote " + lot.getLotId() + ".");
        }

        if (!lotDao.update(lot)) {
            throw new ValidationException("No se pudo actualizar el lote " + lot.getLotId() + ".");
        }
    }

    /** Descuenta kilos vendidos de un lote. */
    public void reduceStock(int lotId, int soldKg) {
        if (soldKg <= 0) {
            throw new ValidationException("Los kilos vendidos deben ser mayores que cero.");
        }

        PergaminoLot lot = lotDao.findById(lotId)
                .orElseThrow(() -> new ValidationException("No existe el lote " + lotId + "."));

        if (soldKg > lot.getAvailableKg()) {
            throw new ValidationException(
                    "Solo quedan " + lot.getAvailableKg() + " kg disponibles.");
        }

        lot.setAvailableKg(lot.getAvailableKg() - soldKg);
        lotDao.update(lot);
    }

    // ------------------------------------------------------------------
    // Baja
    // ------------------------------------------------------------------

    /**
     * Elimina un lote del catálogo.
     *
     * @throws ValidationException si el lote no existe
     */
    public void removeLot(int lotId) {
        if (!lotDao.delete(lotId)) {
            throw new ValidationException("No existe el lote " + lotId + ".");
        }
    }

    /**
     * Elimina un vendedor.
     *
     * <p>La clave foránea de los lotes es {@code ON DELETE RESTRICT}, de modo
     * que la base impide borrar a quien todavía tiene lotes publicados. Aquí se
     * comprueba antes para dar un mensaje que se entienda, en lugar de dejar
     * que aflore un error de integridad referencial.
     *
     * @throws ValidationException si el vendedor no existe o aún tiene lotes
     */
    public void removeProducer(int producerId) {
        boolean tieneLotes = lotDao.findAll().stream()
                .anyMatch(lote -> lote.getProducerId() == producerId);
        if (tieneLotes) {
            throw new ValidationException(
                    "No puedes eliminar un vendedor que todavía tiene lotes publicados.");
        }
        if (!producerDao.delete(producerId)) {
            throw new ValidationException("No existe el vendedor " + producerId + ".");
        }
    }

    // ------------------------------------------------------------------
    // Validación
    // ------------------------------------------------------------------

    /**
     * Comprueba las reglas del dominio antes de tocar la base de datos.
     *
     * <p>El análisis físico es opcional en su totalidad: exigirlo para poder
     * publicar dejaría fuera a la mayoría de caficultores pequeños, que no han
     * mandado su café a un laboratorio. Lo que sí se exige es que, si viene,
     * tenga sentido.
     */
    private void validate(PergaminoLot lot) {
        if (lot == null) {
            throw new ValidationException("El lote no puede ser nulo.");
        }
        if (isBlank(lot.getLotCode())) {
            throw new ValidationException("El código del lote es obligatorio.");
        }
        if (lot.getPricePerKg() == null) {
            throw new ValidationException("El precio por kilogramo es obligatorio.");
        }
        if (lot.getPricePerKg().compareTo(ZERO) < 0) {
            throw new ValidationException("El precio por kilogramo no puede ser negativo.");
        }
        if (lot.getAvailableKg() < 0) {
            throw new ValidationException("Los kilos disponibles no pueden ser negativos.");
        }

        if (lot.getYieldFactor() != null && !isWithinYieldRange(lot.getYieldFactor())) {
            throw new ValidationException(
                    "El factor de rendimiento debe estar entre 80 y 130. "
                    + "Un valor fuera de ese rango es un error de digitación, "
                    + "no un café excepcional.");
        }

        requirePercentage(lot.getMoisturePct(), "La humedad");
        requirePercentage(lot.getHealthyBeanPct(), "El porcentaje de almendra sana");
        requirePercentage(lot.getPasillaPct(), "El porcentaje de pasilla");
        requirePercentage(lot.getBorerDamagePct(), "El daño por broca");
    }

    private boolean isWithinYieldRange(BigDecimal factor) {
        return factor.compareTo(MIN_YIELD_FACTOR) >= 0
                && factor.compareTo(MAX_YIELD_FACTOR) <= 0;
    }

    private void requirePercentage(BigDecimal value, String label) {
        if (value == null) {
            return;
        }
        if (value.compareTo(ZERO) < 0 || value.compareTo(ONE_HUNDRED) > 0) {
            throw new ValidationException(label + " debe estar entre 0 % y 100 %.");
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
