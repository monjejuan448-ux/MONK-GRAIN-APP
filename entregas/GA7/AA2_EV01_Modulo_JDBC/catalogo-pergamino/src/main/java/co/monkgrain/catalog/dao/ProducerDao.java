package co.monkgrain.catalog.dao;

import co.monkgrain.catalog.model.Producer;
import co.monkgrain.catalog.util.DataAccessException;
import co.monkgrain.catalog.util.DatabaseConnection;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Acceso a datos de los vendedores.
 *
 * <p>Es la única capa que conoce JDBC. Ni el servicio ni la interfaz saben que
 * detrás hay SQL, lo que permite cambiar el motor o pasar a un ORM sin tocar
 * las reglas de negocio.
 */
public class ProducerDao {

    private static final String INSERT_SQL =
            "INSERT INTO producers (farm_name, municipality, department, sica_code) "
            + "VALUES (?, ?, ?, ?)";

    private static final String SELECT_ALL_SQL =
            "SELECT producer_id, farm_name, municipality, department, sica_code "
            + "FROM producers ORDER BY farm_name";

    private static final String DELETE_SQL =
            "DELETE FROM producers WHERE producer_id = ?";

    private static final String SELECT_BY_ID_SQL =
            "SELECT producer_id, farm_name, municipality, department, sica_code "
            + "FROM producers WHERE producer_id = ?";

    /**
     * Inserta un vendedor y devuelve su identificador generado.
     *
     * <p>{@code RETURN_GENERATED_KEYS} evita la consulta adicional que haría
     * falta para averiguar el identificador recién creado.
     */
    public int insert(Producer producer) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement =
                     connection.prepareStatement(INSERT_SQL, Statement.RETURN_GENERATED_KEYS)) {

            statement.setString(1, producer.getFarmName());
            statement.setString(2, producer.getMunicipality());
            statement.setString(3, producer.getDepartment());
            statement.setString(4, producer.getSicaCode());
            statement.executeUpdate();

            try (ResultSet keys = statement.getGeneratedKeys()) {
                if (keys.next()) {
                    int id = keys.getInt(1);
                    producer.setProducerId(id);
                    return id;
                }
            }
            throw new DataAccessException("La base de datos no devolvió el identificador generado.");

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible registrar el vendedor.", e);
        }
    }

    /** Todos los vendedores, ordenados por el nombre de la finca. */
    public List<Producer> findAll() {
        List<Producer> producers = new ArrayList<>();
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(SELECT_ALL_SQL);
             ResultSet rows = statement.executeQuery()) {

            while (rows.next()) {
                producers.add(map(rows));
            }
            return producers;

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible consultar los vendedores.", e);
        }
    }

    /**
     * Un vendedor por su identificador.
     *
     * <p>Devuelve {@link Optional} en lugar de {@code null}: obliga a quien
     * llama a decidir qué hacer cuando no existe, en vez de dejar que se le
     * olvide y aparezca un {@code NullPointerException} tres capas más arriba.
     */
    public Optional<Producer> findById(int producerId) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(SELECT_BY_ID_SQL)) {

            statement.setInt(1, producerId);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? Optional.of(map(rows)) : Optional.empty();
            }

        } catch (SQLException e) {
            throw new DataAccessException("No fue posible consultar el vendedor.", e);
        }
    }

    /**
     * Elimina un vendedor.
     *
     * @return {@code true} si la fila existía y se eliminó
     */
    public boolean delete(int producerId) {
        try (Connection connection = DatabaseConnection.open();
             PreparedStatement statement = connection.prepareStatement(DELETE_SQL)) {

            statement.setInt(1, producerId);
            return statement.executeUpdate() > 0;

        } catch (SQLException e) {
            throw new DataAccessException(
                    "No fue posible eliminar el vendedor " + producerId + ".", e);
        }
    }

    /** Traduce una fila del resultado a un objeto de dominio. */
    private Producer map(ResultSet rows) throws SQLException {
        Producer producer = new Producer();
        producer.setProducerId(rows.getInt("producer_id"));
        producer.setFarmName(rows.getString("farm_name"));
        producer.setMunicipality(rows.getString("municipality"));
        producer.setDepartment(rows.getString("department"));
        producer.setSicaCode(rows.getString("sica_code"));
        return producer;
    }
}
