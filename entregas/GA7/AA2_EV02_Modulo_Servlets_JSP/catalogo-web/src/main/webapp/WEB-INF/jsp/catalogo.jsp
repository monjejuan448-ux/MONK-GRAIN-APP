<%--
  Catálogo público. Lo alimenta CatalogServlet por GET.

  Usa los elementos de JSP que pide la evidencia:
    - directiva  <%@ page %> y <%@ taglib %>
    - acción     <jsp:include> para la cabecera
    - expresión  ${...} del lenguaje de expresiones
    - JSTL       <c:forEach>, <c:if>, <c:choose>, <fmt:formatNumber>
--%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>

<c:set var="titulo" value="Catálogo de pergamino — MONK GRAIN" scope="request"/>
<jsp:include page="_cabecera.jsp"/>

<h1>Catálogo de pergamino</h1>
<p class="guia">
  El <strong>factor de rendimiento</strong> son los kilos de pergamino que hay que
  trillar para obtener un saco de 70&nbsp;kg de café excelso.
  <strong>Menos es mejor</strong>: por eso el filtro acota el techo que aceptas.
</p>

<%-- Formulario por GET: el filtro debe quedar en la dirección, para poder
     compartirla o recargarla. --%>
<form class="filtro" method="get" action="${pageContext.request.contextPath}/catalogo">
  <label for="factorMaximo">Factor de rendimiento máximo</label>
  <input type="number" id="factorMaximo" name="factorMaximo"
         min="80" max="130" step="0.01"
         value="${factorMaximo}" placeholder="por ejemplo, 92">
  <button type="submit">Filtrar</button>
  <c:if test="${not empty factorMaximo}">
    <a class="limpiar" href="${pageContext.request.contextPath}/catalogo">Quitar el filtro</a>
  </c:if>
</form>

<p class="resumen">
  <strong>${total}</strong>
  <c:choose>
    <c:when test="${total == 1}">lote disponible</c:when>
    <c:otherwise>lotes disponibles</c:otherwise>
  </c:choose>
</p>

<c:choose>
  <c:when test="${empty lotes}">
    <p class="vacio">
      No hay lotes que cumplan ese criterio.
      <c:if test="${not empty factorMaximo}">
        Prueba con un factor más alto: estás pidiendo un café que rinda mucho.
      </c:if>
    </p>
  </c:when>
  <c:otherwise>
    <table class="tabla">
      <thead>
        <tr>
          <th>Lote</th>
          <th>Variedad</th>
          <th>Factor</th>
          <th>Lectura</th>
          <th>Humedad</th>
          <th class="num">Disponible</th>
          <th class="num">Precio por kilo</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <c:forEach var="lote" items="${lotes}">
          <tr>
            <td><code>${lote.lotCode}</code></td>
            <td>${empty lote.variety ? '—' : lote.variety}</td>
            <td class="num">
              <c:choose>
                <c:when test="${empty lote.yieldFactor}">—</c:when>
                <c:otherwise><fmt:formatNumber value="${lote.yieldFactor}"
                                               minFractionDigits="2"/></c:otherwise>
              </c:choose>
            </td>
            <td><span class="etiqueta">${lote.yieldFactorLabel}</span></td>
            <td class="num">
              <c:choose>
                <c:when test="${empty lote.moisturePct}">—</c:when>
                <c:otherwise>
                  <fmt:formatNumber value="${lote.moisturePct}" minFractionDigits="1"/>&nbsp;%
                  <c:if test="${not lote.moistureInRange}">
                    <span class="aviso" title="Fuera del rango seguro de 10 % a 12 %">!</span>
                  </c:if>
                </c:otherwise>
              </c:choose>
            </td>
            <td class="num">${lote.availableAsCargas}</td>
            <td class="num">
              <fmt:formatNumber value="${lote.pricePerKg}" type="currency"
                                currencySymbol="$" maxFractionDigits="0"/>
            </td>
            <td>
              <a href="${pageContext.request.contextPath}/lotes?accion=detalle&amp;id=${lote.lotId}">Ver</a>
            </td>
          </tr>
        </c:forEach>
      </tbody>
    </table>
  </c:otherwise>
</c:choose>

<jsp:include page="_pie.jsp"/>
