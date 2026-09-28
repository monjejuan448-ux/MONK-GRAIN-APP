# Plan Pre-Desarrollo — MONK GRAIN (Marketplace B2B de Café)

**Visión oficial confirmada:** MONK GRAIN es un marketplace digital que conecta productores de café colombianos con compradores internacionales (publicación de productos, negociación, generación de orden de compra, validación de certificaciones y seguimiento logístico). Queda descartado el módulo de gestión agrícola con calendario lunar/sensores IoT (Guía 3: Arquitectura del Software, Diagrama de Clases, Diagrama de Despliegue e Informe de Entregables tal como estaban redactados) y la "Ficha Técnica MONK GRAIN" con stack MERN, por no corresponder a esta visión.

**Artefactos reutilizables como base:**
- Las 9 historias de usuario de GUIA N1 / GUIA N2 (docs "Diagramas y documentación de actividades", "Historias de Usuario del Proyecto", tabla de Guía 1): Productor, Comprador, Administrador, Operador Logístico.
- El "Modelo conceptual y lógico" de Guía 3 (Finca, LoteCafe, Productor, Cliente, Orden, ItemOrden, Inventario, UsuarioApp) — es el único artefacto técnico de Guía 3 compatible con el marketplace, aunque necesita ajustes.
- La forma general del diagrama de despliegue de Guía 3 (API Gateway, microservicios, BD, mensajería), quitando los nodos de sensores/clima.

---

## Fase 0 — Cierre de alcance

| Tarea | Estado |
|---|---|
| Confirmar visión única del producto (marketplace B2B de café) | ✅ Confirmado |
| Descartar módulo agrícola y Ficha Técnica MERN | ✅ Confirmado |
| Decidir el stack tecnológico (ADR de una página) | ⏳ **Pendiente — tu decisión** |
| Decidir si pagos vía API bancaria y logística de exportación (GPS/blockchain) van en el MVP o se posponen a fase 2 | ⏳ **Pendiente — tu decisión** |

No se avanza a la Fase 2 (diseño técnico) sin cerrar el stack, porque de él depende cómo se modela la persistencia y el despliegue.

---

## Fase 1 — Consolidación de requisitos (3-5 días)

1. Fusionar los dos instrumentos de encuesta ("Formulario Encuesta" e "Instrumento de Recolección de Información") en uno solo; si aún no se ha aplicado a encuestados reales, aplicarlo — ambos documentos actuales son plantillas vacías, sin datos reales de productores/compradores.
2. Unificar la tabla de Historias de Usuario en un solo backlog con ID inmutable (formato "HU-01" consistente), eliminando la versión suelta "HU01" de Guía 1 que tiene contenido distinto para el mismo tema.
3. Resolver la cobertura de actores: agregar historias de usuario para "Operador Logístico" (hoy tiene casos de uso en el diagrama pero ninguna HU asociada) y decidir si "Entidad de apoyo" y "Cliente final" se mantienen como roles independientes o se fusionan con los 4 actores principales.
4. Construir una matriz de trazabilidad única RF ↔ CU ↔ HU ↔ Clase ↔ Tabla, en una sola hoja de cálculo o tablero.
5. Completar las fichas técnicas de recolección de datos faltantes (hoy solo existen para HU-01, HU-02, HU-04, HU-08; faltan HU-03, HU-05, HU-06, HU-07, HU-09), replicando el formato ya usado (campo/tipo/obligatoriedad/regla de validación).

---

## Fase 2 — Diseño técnico definitivo (5-7 días)

1. Rehacer el diagrama de clases desde cero, tomando como base las entidades del "Modelo conceptual y lógico" (Finca, LoteCafe, Productor, Cliente, Orden, ItemOrden, Inventario, UsuarioApp) y agregando los roles de negocio que hoy faltan ahí: Comprador, Administrador y Operador Logístico como especializaciones o roles de `UsuarioApp`.
2. Ajustar el modelo relacional:
   - Corregir `LOTE_CAFE.puntajeScore DECIMAL(3,2)` → `DECIMAL(5,2)` (el rango declarado es 0.00–100.00, y `DECIMAL(3,2)` solo admite hasta 9.99).
   - Definir explícitamente los valores permitidos de cada campo `ENUM` que hoy queda ambiguo.
   - Agregar tabla/entidad para certificaciones (hoy la HU-08 de certificaciones no tiene tabla equivalente en el modelo).
3. Producir un único diagrama de casos de uso final (hoy existen dos PDFs duplicados byte a byte: eliminar uno) y un diagrama de secuencia para al menos el flujo de negociación/orden de compra, que hoy no existe en ningún documento.
4. Adaptar el diagrama de despliegue de Guía 3 al marketplace: mantener API Gateway, microservicios, BD y cola de mensajería; quitar los nodos de sensores IoT/clima que no aplican; agregar el nodo de integración con el sistema de pagos y el sistema de tracking logístico externo (ya señalados como actores externos en el diagrama de casos de uso de Guía 1).
5. Formalizar en un ADR el stack decidido en Fase 0 y reflejarlo en el diagrama de despliegue.

---

## Fase 3 — Verificación y cierre de calidad documental (2-3 días)

1. Elegir una sola versión de las listas de chequeo (recomendado: la de 8 ítems / 3 niveles Cumple-Parcial-No Cumple, ya usada en dos entregas) y descartar la versión de 5 ítems / Sí-No.
2. Diligenciar esa lista realmente contra los artefactos ya corregidos de Fase 1 y 2, con fecha y responsable — hoy las listas están vacías pese a que el informe de evaluación reporta porcentajes de cumplimiento sin evidencia de respaldo.
3. Recalcular el informe de evaluación con la fórmula que el propio documento define (`%Cumplimiento = Cumple/Total × 100`), verificando el promedio con una hoja de cálculo (el informe anterior declaraba 87% cuando el cálculo real de sus propios datos daba 90%).
4. Pasar corrección ortográfica/editorial sobre toda la documentación (typos recurrentes como "SERVIICIO", "CONCLUCIONES", "MONKGRAIN" sin espacio; fragmentos de texto residual de búsquedas web sin depurar).

---

## Fase 4 — Preparación para desarrollo (2-3 días)

1. Backlog priorizado con estimaciones reales de esfuerzo (reemplazar las marcas "(ejemplo, puedes ajustarlo)" por valores definitivos, idealmente estimados con planning poker).
2. Definir **Definition of Ready**: una HU no entra a sprint si no tiene criterios de aceptación, ficha técnica de datos, mockup/wireframe y trazabilidad a un RF.
3. Definir **Definition of Done**: código + pruebas + lista de chequeo LC-3 (código) y LC-4 (pruebas) aplicada + documentación actualizada.
4. Configurar el entorno técnico (repositorio, CI básico, tablero Scrum) según el stack decidido en Fase 0.

---

## Duración estimada y criterio de salida

**Duración total de esta fase de estabilización: 2.5 a 3.5 semanas** antes de abrir el primer sprint de desarrollo.

**Definition of Ready para pasar a desarrollo:**
- [ ] Stack tecnológico decidido y documentado en un ADR.
- [ ] Alcance de pagos/logística en el MVP decidido explícitamente.
- [ ] Un solo diagrama de casos de uso, un solo diagrama de clases, un solo modelo relacional — coherentes entre sí y con las 9 HU.
- [ ] Backlog de HU con ID único, sin duplicados, con estimaciones reales.
- [ ] Matriz de trazabilidad RF↔CU↔HU↔Clase completa.
- [ ] Listas de chequeo diligenciadas con evidencia real, ≥80% de cumplimiento genuino.
- [ ] Encuesta de recolección de información aplicada a usuarios reales (productores/compradores), no solo la plantilla.
