<%-- Ficha completa del lote con su análisis físico. --%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>
<%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>

<c:set var="titulo" value="Lote ${lote.lotCode} — MONK GRAIN" scope="request"/>
<jsp:include page="_cabecera.jsp"/>

<h1>Lote <code>${lote.lotCode}</code></h1>

<dl class="ficha">
  <dt>Variedad</dt>
  <dd>${empty lote.variety ? 'Sin declarar' : lote.variety}</dd>

  <dt>Factor de rendimiento</dt>
  <dd>
    <c:choose>
      <c:when test="${empty lote.yieldFactor}">Sin declarar</c:when>
      <c:otherwise>
        <fmt:formatNumber value="${lote.yieldFactor}" minFractionDigits="2"/>
        · <span class="etiqueta">${lote.yieldFactorLabel}</span>
      </c:otherwise>
    </c:choose>
  </dd>

  <dt>Humedad</dt>
  <dd>
    <c:choose>
      <c:when test="${empty lote.moisturePct}">Sin declarar</c:when>
      <c:otherwise>
        <fmt:formatNumber value="${lote.moisturePct}" minFractionDigits="2"/>&nbsp;%
        <c:choose>
          <c:when test="${lote.moistureInRange}"> · en el rango seguro</c:when>
          <c:otherwise> · <strong>fuera del rango de 10 % a 12 %</strong></c:otherwise>
        </c:choose>
      </c:otherwise>
    </c:choose>
  </dd>

  <dt>Almendra sana</dt>
  <dd><c:choose><c:when test="${empty lote.healthyBeanPct}">Sin declarar</c:when>
      <c:otherwise><fmt:formatNumber value="${lote.healthyBeanPct}"
                   minFractionDigits="2"/>&nbsp;%</c:otherwise></c:choose></dd>

  <dt>Pasilla</dt>
  <dd><c:choose><c:when test="${empty lote.pasillaPct}">Sin declarar</c:when>
      <c:otherwise><fmt:formatNumber value="${lote.pasillaPct}"
                   minFractionDigits="2"/>&nbsp;%</c:otherwise></c:choose></dd>

  <dt>Daño por broca</dt>
  <dd><c:choose><c:when test="${empty lote.borerDamagePct}">Sin declarar</c:when>
      <c:otherwise><fmt:formatNumber value="${lote.borerDamagePct}"
                   minFractionDigits="2"/>&nbsp;%</c:otherwise></c:choose></dd>

  <dt>Disponible</dt>
  <dd>${lote.availableAsCargas}</dd>

  <dt>Precio por kilogramo</dt>
  <dd><fmt:formatNumber value="${lote.pricePerKg}" type="currency"
                        currencySymbol="$" maxFractionDigits="0"/></dd>

  <dt>Valor del lote</dt>
  <dd><fmt:formatNumber value="${lote.totalValue}" type="currency"
                        currencySymbol="$" maxFractionDigits="0"/></dd>

  <dt>Cosecha</dt>
  <dd>${empty lote.harvestDate ? 'Sin declarar' : lote.harvestDate}</dd>

  <dt>Estado</dt>
  <dd>${lote.published ? 'Publicado en el catálogo' : 'Borrador'}</dd>
</dl>

<p class="guia">
  El análisis lo declara el vendedor y MONK GRAIN no lo verifica. Antes de una
  compra por volumen conviene pedir muestra y hacer análisis propio.
</p>

<p><a href="${pageContext.request.contextPath}/catalogo">← Volver al catálogo</a></p>

<jsp:include page="_pie.jsp"/>
