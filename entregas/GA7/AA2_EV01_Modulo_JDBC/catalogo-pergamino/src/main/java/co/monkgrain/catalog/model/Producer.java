package co.monkgrain.catalog.model;

/**
 * Vendedor de pergamino: un caficultor, una finca o una cooperativa.
 *
 * <p>Objeto de dominio puro: no sabe de JDBC ni de pantallas. Esa separación es
 * lo que permite probar las reglas de negocio sin levantar una base de datos.
 */
public class Producer {

    private int producerId;
    private String farmName;
    private String municipality;
    private String department;
    private String sicaCode;

    public Producer() {
    }

    public Producer(String farmName, String municipality, String department, String sicaCode) {
        this.farmName = farmName;
        this.municipality = municipality;
        this.department = department;
        this.sicaCode = sicaCode;
    }

    public int getProducerId() {
        return producerId;
    }

    public void setProducerId(int producerId) {
        this.producerId = producerId;
    }

    public String getFarmName() {
        return farmName;
    }

    public void setFarmName(String farmName) {
        this.farmName = farmName;
    }

    public String getMunicipality() {
        return municipality;
    }

    public void setMunicipality(String municipality) {
        this.municipality = municipality;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getSicaCode() {
        return sicaCode;
    }

    public void setSicaCode(String sicaCode) {
        this.sicaCode = sicaCode;
    }

    /** Dónde está la finca, para mostrarlo de un vistazo. */
    public String getOrigin() {
        return municipality + ", " + department;
    }

    @Override
    public String toString() {
        return String.format("[%d] %s — %s", producerId, farmName, getOrigin());
    }
}
