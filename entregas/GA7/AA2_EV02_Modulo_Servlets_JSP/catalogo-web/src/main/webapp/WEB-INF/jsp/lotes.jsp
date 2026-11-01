<%-- Bandeja del vendedor: todos sus lotes, publicados o no. --%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>

<c:set var="titulo" value="Mis lotes — MONK GRAIN" scope="request"/>
<jsp:include page="_cabecera.jsp"/>

<h1>Mis lotes</h1>

<c:if test="${not empty mensaje}">
  <p class="mensaje">${mensaje}</p>
</c:if>

<c:choose>
  <c:when test="${empty lotes}">
    <p class="vacio">
      Todavía no has publicado ningún lote.
      <a href="${pageContext.request.contextPath}/lotes?accion=nuevo">Publica el primero</a>.
    </p>
  </c:when>
  <c:otherwise>
    <table class="tabla">
      <thead>
        <tr>
          <th>Lote</th>
          <th>Factor</th>
          <th class="num">Disponible</th>
          <th class="num">Precio</th>
          <th>Estado</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <c:forEach var="lote" items="${lotes}">
          <tr>
            <td>
              <a href="${pageContext.request.contextPath}/lotes?accion=detalle&amp;id=${lote.lotId}">
                <code>${lote.lotCode}</code>
              </a>
            </td>
            <td>${lote.yieldFactorLabel}</td>
            <td class="num">${lote.availableAsCargas}</td>
            <td class="num">
              <fmt:formatNumber value="${lote.pricePerKg}" type="currency"
                                currencySymbol="$" maxFractionDigits="0"/>
            </td>
            <td>
              <c:choose>
                <c:when test="${lote.published}"><span class="etiqueta ok">Publicado</span></c:when>
                <c:otherwise><span class="etiqueta">Borrador</span></c:otherwise>
              </c:choose>
            </td>
            <td>
              <%-- Eliminar va por POST y no por un enlace: una acción que
                   borra no debe poder dispararse con una visita. --%>
              <form method="post" action="${pageContext.request.contextPath}/lotes"
                    onsubmit="return confirm('¿Eliminar el lote ${lote.lotCode}?');">
                <input type="hidden" name="accion" value="eliminar">
                <input type="hidden" name="id" value="${lote.lotId}">
                <button type="submit" class="peligro">Eliminar</button>
              </form>
            </td>
          </tr>
        </c:forEach>
      </tbody>
    </table>
  </c:otherwise>
</c:choose>

<jsp:include page="_pie.jsp"/>
