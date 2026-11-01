<%--
  Cabecera común de todas las páginas.

  Se incluye con <jsp:include> en lugar de repetirse: es el elemento de JSP
  que evita que una barra de navegación quede distinta en cada pantalla.
--%>
<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${empty titulo ? 'MONK GRAIN' : titulo}</title>
  <link rel="stylesheet" href="${pageContext.request.contextPath}/estilo.css">
</head>
<body>
<header class="barra">
  <a class="marca" href="${pageContext.request.contextPath}/catalogo">MONK&nbsp;GRAIN</a>
  <nav>
    <a href="${pageContext.request.contextPath}/catalogo">Catálogo</a>
    <a href="${pageContext.request.contextPath}/lotes">Mis lotes</a>
    <a href="${pageContext.request.contextPath}/lotes?accion=nuevo">Publicar lote</a>
  </nav>
</header>
<main class="contenido">
