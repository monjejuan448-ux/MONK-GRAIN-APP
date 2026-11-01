<%--
  Formulario de publicación de un lote. Se envía por POST a LotServlet.

  El formulario valida en el navegador (required, min, max, step) y el
  servidor vuelve a validar: la comprobación del navegador se salta con
  una petición directa, así que no es una defensa, es una comodidad.
--%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>

<c:set var="titulo" value="Publicar un lote — MONK GRAIN" scope="request"/>
<jsp:include page="_cabecera.jsp"/>

<h1>Publicar un lote de pergamino</h1>

<c:if test="${not empty param.mensaje}">
  <p class="mensaje">${param.mensaje}</p>
</c:if>

<c:choose>
  <c:when test="${empty productores}">
    <p class="vacio">
      Todavía no hay vendedores registrados. Registra uno primero: un lote
      siempre pertenece a una finca.
    </p>
  </c:when>
  <c:otherwise>
    <form class="formulario" method="post"
          action="${pageContext.request.contextPath}/lotes">
      <input type="hidden" name="accion" value="crear">

      <fieldset>
        <legend>Identificación</legend>

        <label for="productor">Vendedor</label>
        <select id="productor" name="productor" required>
          <c:forEach var="p" items="${productores}">
            <option value="${p.producerId}">${p.farmName} — ${p.origin}</option>
          </c:forEach>
        </select>

        <label for="codigo">Código del lote</label>
        <input type="text" id="codigo" name="codigo" required maxlength="60"
               placeholder="MIR-2026-001">
        <small>Con el que identificas el lote en tu finca. No puede repetirse.</small>

        <label for="variedad">Variedad</label>
        <input type="text" id="variedad" name="variedad" maxlength="80"
               placeholder="Caturra, Castillo, Colombia…">
      </fieldset>

      <fieldset>
        <legend>Análisis físico</legend>
        <p class="guia">
          Todo opcional. Un lote con factor y humedad declarados se vende mejor,
          pero exigirlo dejaría fuera a quien no ha mandado su café a un
          laboratorio.
        </p>

        <label for="factor">Factor de rendimiento</label>
        <input type="number" id="factor" name="factor"
               min="80" max="130" step="0.01" placeholder="88.50">
        <small>Entre 80 y 130. Menos es mejor; el estándar de la Federación es 94.</small>

        <label for="humedad">Humedad (%)</label>
        <input type="number" id="humedad" name="humedad"
               min="0" max="100" step="0.01" placeholder="11.20">
        <small>El rango seguro de almacenamiento es de 10 % a 12 %.</small>

        <label for="almendraSana">Almendra sana (%)</label>
        <input type="number" id="almendraSana" name="almendraSana"
               min="0" max="100" step="0.01">

        <label for="pasilla">Pasilla (%)</label>
        <input type="number" id="pasilla" name="pasilla"
               min="0" max="100" step="0.01">

        <label for="broca">Daño por broca (%)</label>
        <input type="number" id="broca" name="broca"
               min="0" max="100" step="0.01">
      </fieldset>

      <fieldset>
        <legend>Condiciones comerciales</legend>

        <label for="precio">Precio por kilogramo (COP)</label>
        <input type="number" id="precio" name="precio" required
               min="0" step="0.01" placeholder="24500">

        <label for="kilos">Kilos disponibles</label>
        <input type="number" id="kilos" name="kilos" required
               min="0" step="1" placeholder="1250">
        <small>Una carga son 125 kg.</small>

        <label for="cosecha">Fecha de cosecha</label>
        <input type="date" id="cosecha" name="cosecha">

        <label class="casilla">
          <input type="checkbox" name="publicado" checked>
          Publicar en el catálogo
        </label>
      </fieldset>

      <button type="submit">Publicar lote</button>
    </form>
  </c:otherwise>
</c:choose>

<h2>Registrar un vendedor</h2>
<form class="formulario compacto" method="post"
      action="${pageContext.request.contextPath}/lotes">
  <input type="hidden" name="accion" value="productor">

  <label for="finca">Nombre de la finca</label>
  <input type="text" id="finca" name="finca" required maxlength="150">

  <label for="municipio">Municipio</label>
  <input type="text" id="municipio" name="municipio" required maxlength="100">

  <label for="departamento">Departamento</label>
  <input type="text" id="departamento" name="departamento" required maxlength="100">

  <label for="sica">Código SICA</label>
  <input type="text" id="sica" name="sica" maxlength="40">
  <small>Del Sistema de Información Cafetera. No lo contrastamos con la Federación.</small>

  <button type="submit">Registrar vendedor</button>
</form>

<jsp:include page="_pie.jsp"/>
