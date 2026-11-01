package co.monkgrain.catalog.dao;

import co.monkgrain.catalog.model.PergaminoLot;
import co.monkgrain.catalog.util.DataAccessException;
import co.monkgrain.catalog.util.DatabaseConnection;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Acceso a datos de los lotes de pergamino: las cuatro operaciones del CRUD.
 *
 * <p>Todas las consultas usan {@link PreparedStatement} con parámetros y nunca
 * concatenación de cadenas. No es una preferencia de estilo: concatenar la
 * entrada del usuario dentro del SQL es exactamente lo que permite una
 * inyección, y basta con que se olvide una vez.
 *
 * <p>Cada método abre su conexión con {@code try-with-resources} y la cierra
 * aunque haya excepción. Una conexión que se queda abierta agota el cupo del
 * servidor y el fallo aparece mucho después, en una operación que no tiene la
 * culpa.
 */
public class PergaminoLotDao {

    private static final String INSERT_SQL =
            "INSERT INTO pergamino_lots ("
            + "  producer_id, lot_code, variety, yield_factor, moisture_pct,"
            + "  healthy_bean_pct, pasilla_pct, borer_damage_pct,"
            + "  price_per_kg, available_kg, harvest_date, published"
            + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

    private static final String COLUMNS =
            "lot_id, producer_id, lot_code, variety, yield_factor, moisture_pct, "
            + "healthy_bean_pct, pasilla_pct, borer_damage_pct, price_per_kg, "
            + "available_kg, harvest_date, published, created_at";

    private static final String SELECT_ALL_SQL =
            "SELECT " + COLUMNS + " FROM pergamino_lots ORDER BY lot_id";

    private static final String SELECT_BY_ID_SQL =
            "SELECT " + COLUMNS + " FROM pergamino_lots WHERE lot_id = ?";

    /**
     * Filtro del catálogo. El factor se acota por su <strong>máximo</strong>
     * porque menos es mejor: lo que el comprador fija es el techo que acepta.
     * El orden es ascendente, con los lotes sin factor declarado al final: un
     * lote que no declara nada no puede afirmar que cumple nada.
     */
    private static final String SELECT_PUBLISHED_SQL =
            "SELECT " + COLUMNS + " FROM pergamino_lots "
            + "WHERE published = TRUE AND available_kg > 0 "
            + "  AND (? IS NULL OR yield_factor <= ?) "
            + "ORDER BY yield_factor ASC NULLS LAST, price_per_kg ASC";

    private static final String UPDATE_SQL =
            "UPDATE pergamino_lots SET "
            + "  variety = ?, yield_factor = ?, moisture_pct = ?,"
            + "  healthy_bean_pct = ?, pasilla_pct = ?, borer_damage_pct = ?,"
            + "  price_per_kg = ?, available_kg = ?, harvest_date = ?, published = ? "
            + "WHERE lot_id = ?";

    private static final String DELETE_SQL =
            "DELETE FROM pergamino_lots WHERE lot_id = ?";

    private static final String EXISTS_CODE_SQL =
            "SELECT 1 FROM pergamino_lots WHERE producer_id = ? AND lot_code = ?";

    // ------------------------------------------------------------------
    // Inserción
    // ------------------------------------------------------------------

    /**
     * Registra un lote nuevo y devuelve su identificador generado.
     *
     * @param lot lote a registrar; se le asigna el identificador al volver
     * @return identificador del lote creado
     */
    public int insert(PergaminoLot lot) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement =
                     connection.prepareStatement(INSERT_SQL, Statement.RETURN_GENERATED_KEYS)) {

            statement.setInt(1, lot.getProducerId());
            statement.setString(2, lot.getLotCode());
            statement.setString(3, lot.getVariety());
            setDecimal(statement, 4, lot.getYieldFactor());
            setDecimal(statement, 5, lot.getMoisturePct());
            setDecimal(statement, 6, lot.getHealthyBeanPct());
            setDecimal(statement, 7, lot.getPasillaPct());
            setDecimal(statement, 8, lot.getBorerDamagePct());
            statement.setBigDecimal(9, lot.getPricePerKg());
            statement.setInt(10, lot.getAvailableKg());
            setDate(statement, 11, lot.getHarvestDate());
            statement.setBoolean(12, lot.isPublished());

            statement.executeUpdate();

            try (ResultSet keys = statement.getGeneratedKeys()) {
                if (keys.next()) {
                    int id = keys.getInt(1);
                    lot.setLotId(id);
                    return id;
                }
            }
            throw new DataAccessException("La base de datos no devolvió el identificador generado.");

        } catch (SQLException e) {
            throw new DataAccessException(
                    "No fue posible registrar el lote " + lot.getLotCode() + ".", e);
        }
    }

    // ------------------------------------------------------------------
    // Consulta
    // ------------------------------------------------------------------

    /** Todos los lotes, publicados o no. Es la vista del vendedor. */
    public List<PergaminoLot> findAll() {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(SELECT_ALL_SQL);
             ResultSet rows = statement.executeQuery()) {

            List<PergaminoLot> lots = new ArrayList<>();
            while (rows.next()) {
                lots.add(map(rows));
            }
            return lots;

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible consultar los lotes.", e);
        }
    }

    /** Un lote por su identificador, vacío si no existe. */
    public Optional<PergaminoLot> findById(int lotId) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(SELECT_BY_ID_SQL)) {

            statement.setInt(1, lotId);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? Optional.of(map(rows)) : Optional.empty();
            }

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible consultar el lote " + lotId + ".", e);
        }
    }

    /**
     * Lo que ve un comprador: solo lo publicado y con existencias.
     *
     * @param maxYieldFactor techo de factor que acepta, o {@code null} para no filtrar
     */
    public List<PergaminoLot> findPublished(BigDecimal maxYieldFactor) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(SELECT_PUBLISHED_SQL)) {

            // El mismo parámetro va dos veces: una para el `IS NULL` que
            // desactiva el filtro y otra para la comparación.
            setDecimal(statement, 1, maxYieldFactor);
            setDecimal(statement, 2, maxYieldFactor);

            try (ResultSet rows = statement.executeQuery()) {
                List<PergaminoLot> lots = new ArrayList<>();
                while (rows.next()) {
                    lots.add(map(rows));
                }
                return lots;
            }

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible consultar el catálogo.", e);
        }
    }

    /** Si el vendedor ya tiene un lote con ese código. */
    public boolean existsLotCode(int producerId, String lotCode) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(EXISTS_CODE_SQL)) {

            statement.setInt(1, producerId);
            statement.setString(2, lotCode);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next();
            }

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible verificar el código del lote.", e);
        }
    }

    // ------------------------------------------------------------------
    // Actualización
    // ------------------------------------------------------------------

    /**
     * Actualiza un lote existente.
     *
     * <p>No se permite cambiar el productor ni el código del lote: son su
     * identidad comercial, y moverlos dejaría sin sentido las reclamaciones ya
     * presentadas contra él.
     *
     * @return {@code true} si la fila existía y se modificó
     */
    public boolean update(PergaminoLot lot) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(UPDATE_SQL)) {

            statement.setString(1, lot.getVariety());
            setDecimal(statement, 2, lot.getYieldFactor());
            setDecimal(statement, 3, lot.getMoisturePct());
            setDecimal(statement, 4, lot.getHealthyBeanPct());
            setDecimal(statement, 5, lot.getPasillaPct());
            setDecimal(statement, 6, lot.getBorerDamagePct());
            statement.setBigDecimal(7, lot.getPricePerKg());
            statement.setInt(8, lot.getAvailableKg());
            setDate(statement, 9, lot.getHarvestDate());
            statement.setBoolean(10, lot.isPublished());
            statement.setInt(11, lot.getLotId());

            return statement.executeUpdate() > 0;

        } catch (SQLException e) {
            throw new DataAccessException(
                    "No fue posible actualizar el lote " + lot.getLotId() + ".", e);
        }
    }

    // ------------------------------------------------------------------
    // Eliminación
    // ------------------------------------------------------------------

    /**
     * Elimina un lote.
     *
     * @return {@code true} si la fila existía y se eliminó
     */
    public boolean delete(int lotId) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(DELETE_SQL)) {

            statement.setInt(1, lotId);
            return statement.executeUpdate() > 0;

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible eliminar el lote " + lotId + ".", e);
        }
    }

    // ------------------------------------------------------------------
    // Utilidades internas
    // ------------------------------------------------------------------

    /**
     * Asigna un decimal que puede faltar.
     *
     * <p>{@code setBigDecimal(null)} funciona en PostgreSQL pero no en todos
     * los controladores; {@code setNull} con el tipo explícito es portable y
     * deja claro que la ausencia es intencional.
     */
    private void setDecimal(PreparedStatement statement, int index, BigDecimal value)
            throws SQLException {
        if (value == null) {
            statement.setNull(index, Types.NUMERIC);
        } else {
            statement.setBigDecimal(index, value);
        }
    }

    private void setDate(PreparedStatement statement, int index, java.time.LocalDate value)
            throws SQLException {
        if (value == null) {
            statement.setNull(index, Types.DATE);
        } else {
            statement.setDate(index, Date.valueOf(value));
        }
    }

    /**
     * Traduce una fila a un objeto de dominio.
     *
     * <p>Los decimales se leen con {@code getBigDecimal}, que devuelve
     * {@code null} cuando la columna lo es, y las fechas se convierten a los
     * tipos de {@code java.time} para que el dominio no arrastre las clases
     * heredadas de {@code java.sql}.
     */
    private PergaminoLot map(ResultSet rows) throws SQLException {
        PergaminoLot lot = new PergaminoLot();
        lot.setLotId(rows.getInt("lot_id"));
        lot.setProducerId(rows.getInt("producer_id"));
        lot.setLotCode(rows.getString("lot_code"));
        lot.setVariety(rows.getString("variety"));
        lot.setYieldFactor(rows.getBigDecimal("yield_factor"));
        lot.setMoisturePct(rows.getBigDecimal("moisture_pct"));
        lot.setHealthyBeanPct(rows.getBigDecimal("healthy_bean_pct"));
        lot.setPasillaPct(rows.getBigDecimal("pasilla_pct"));
        lot.setBorerDamagePct(rows.getBigDecimal("borer_damage_pct"));
        lot.setPricePerKg(rows.getBigDecimal("price_per_kg"));
        lot.setAvailableKg(rows.getInt("available_kg"));

        Date harvest = rows.getDate("harvest_date");
        lot.setHarvestDate(harvest == null ? null : harvest.toLocalDate());

        lot.setPublished(rows.getBoolean("published"));

        Timestamp created = rows.getTimestamp("created_at");
        lot.setCreatedAt(created == null ? null : created.toLocalDateTime());

        return lot;
    }
}
