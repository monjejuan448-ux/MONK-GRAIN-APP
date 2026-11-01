<%--
  Página de error. La alcanzan los servlets al capturar una ValidationException
  y también el contenedor, por la declaración <error-page> de web.xml.

  `isErrorPage="true"` da acceso al objeto implícito `exception`.
--%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" isErrorPage="true" %>
<%@ taglib prefix="c" uri="jakarta.tags.core" %>

<c:set var="titulo" value="No pudimos continuar — MONK GRAIN" scope="request"/>
<jsp:include page="_cabecera.jsp"/>

<h1>No pudimos continuar</h1>

<c:choose>
  <c:when test="${not empty mensajeError}">
    <p class="error">${mensajeError}</p>
  </c:when>
  <c:when test="${not empty requestScope['jakarta.servlet.error.message']}">
    <p class="error">${requestScope['jakarta.servlet.error.message']}</p>
  </c:when>
  <c:otherwise>
    <p class="error">Ocurrió un problema al procesar tu solicitud.</p>
  </c:otherwise>
</c:choose>

<p>
  <a href="${pageContext.request.contextPath}/catalogo">Volver al catálogo</a> ·
  <a href="${pageContext.request.contextPath}/lotes">Ir a mis lotes</a>
</p>

<jsp:include page="_pie.jsp"/>
