# MONK GRAIN — Fase 6: Identidad Visual y Frontend

Documenta el sistema de diseño y la base del frontend web. Las páginas de catálogo, carrito y paneles se construyen sobre estos cimientos en las fases 8 y 9.

---

## 1. Identidad de marca

### Concepto del logo

El símbolo combina **un grano de café con la silueta de una montaña**: el grano es el producto, la montaña es el origen de altura que define su calidad. La hendidura central del grano continúa la línea del valle entre las dos cumbres, de modo que ambas lecturas comparten el mismo trazo en lugar de ser dos dibujos superpuestos.

Se implementa como SVG en [`Logo.tsx`](../web/src/components/shared/Logo.tsx), con dos variantes:
- **Completa** (`Logo`) — símbolo más nombre y descriptor "Café de origen".
- **Símbolo** (`LogoMark`) — para espacios reducidos, favicon y usos decorativos.

El modo monocromático permite usarlo sobre fondos oscuros y en impresión a una tinta sin rehacer el archivo.

### Paleta

| Color | Valor | Uso |
|---|---|---|
| Café oscuro | `#3B2417` | Texto principal, fondo de portada |
| Café tostado | `#6F4E37` | Color primario de acción |
| Verde bosque | `#1F4D3A` | Color secundario, sección de trazabilidad |
| Verde suave | `#7A9B76` | Acentos de sostenibilidad |
| Crema | `#F4EBDD` | Fondos suaves, texto sobre oscuro |
| Dorado suave | `#C79A55` | Destacados, calificaciones, llamados a la acción |
| Blanco cálido | `#FFFDF8` | Fondo general |

Los colores no se usan directamente en los componentes: se declaran como **variables CSS en HSL** y se exponen mediante roles semánticos (`primary`, `secondary`, `muted`, `accent`, `destructive`). Esto tiene dos consecuencias prácticas:

1. El **modo oscuro** redefine los mismos tokens en un solo lugar; ningún componente necesita saber en qué tema está ni llevar clases `dark:` repetidas.
2. Un cambio de marca futuro se aplica editando siete variables, no rastreando códigos hexadecimales por todo el código.

El formato HSL (en lugar de hexadecimal) permite que Tailwind module la opacidad: `bg-primary/10` produce el mismo tono al 10 %.

### Tipografía

- **Display** (`font-display`) — títulos y nombres de producto. Transmite el carácter artesanal.
- **Sans** (`font-sans`) — cuerpo de texto e interfaz. Prioriza legibilidad.

---

## 2. Decisiones de accesibilidad

No son un añadido posterior: están en la base del sistema.

| Decisión | Dónde | Por qué |
|---|---|---|
| Foco siempre visible (`:focus-visible` con anillo) | `globals.css` | Sin foco visible, la navegación por teclado es imposible de seguir (HU-TRX-01, CA2) |
| Enlace "Saltar al contenido" | Layout público | Evita recorrer toda la navegación en cada página |
| `prefers-reduced-motion` respetado | `globals.css` | Las animaciones pueden provocar malestar; el sistema operativo ya expresa esa preferencia |
| `aria-busy` en botones cargando | `Button` | El lector de pantalla no percibe el cambio visual del indicador |
| Iconos decorativos con `aria-hidden` | Todos | Un icono junto a texto duplicaría el anuncio |
| Botones de solo icono con `aria-label` | Navbar | Sin texto visible, el nombre accesible debe declararse |
| Enlaces reales para navegación | Navbar | Un `<Link>` dentro de un `<button>` es HTML inválido y confunde a los lectores de pantalla |
| Texto del enlace = nombre del producto | `ProductCard` | Un "ver más" sin contexto es inútil al navegar por lista de enlaces |
| Estados de carga, vacío y error definidos | `states.tsx` | Toda vista con datos remotos los necesita; tenerlos como componentes evita improvisar |

---

## 3. Estructura del frontend

```
web/src/
├── app/
│   ├── layout.tsx           Raíz: idioma, metadatos, fuentes
│   └── (public)/
│       ├── layout.tsx       Navegación, pie de página, enlace de salto
│       └── page.tsx         Página de inicio
├── components/
│   ├── ui/                  Primitivas: Button, Card, Badge
│   └── shared/              Logo, Navbar, Footer, estados
├── features/
│   └── catalog/components/  ProductCard
├── lib/
│   ├── api.ts               Cliente HTTP y errores tipados
│   ├── format.ts            Moneda, fechas, peso, altitud
│   └── utils.ts             Composición de clases
├── types/catalog.ts         Tipos en espejo con el backend
└── styles/globals.css       Tokens de color y capas base
```

### Cliente HTTP

[`api.ts`](../web/src/lib/api.ts) traduce la respuesta de error estructurada del backend (`{error: {code, message, details}}`) a una excepción `ApiError` tipada, con los errores por campo ya extraídos en un diccionario. La interfaz puede así mostrar el mensaje junto al campo correspondiente en lugar de un error genérico.

### Formateo

Toda la localización vive en [`format.ts`](../web/src/lib/format.ts), nunca incrustada en componentes. Detalles que importan:

- **Los importes llegan del backend como cadena**, no como número. En JSON, `number` es punto flotante y perdería la precisión que `NUMERIC(14,2)` protege en la base de datos (ADR-04).
- **El peso colombiano se muestra sin decimales**, que es la práctica comercial real.
- La configuración regional se lee de una variable de entorno, no está fija en el código (RNF-09).

---

## 4. Página de inicio

Cubre los elementos definidos en el brief y HU-VIS-01:

| Sección | Contenido |
|---|---|
| Navegación | Logo, buscador, "Comprar café", "Vender café", carrito, favoritos, cuenta |
| Portada | Mensaje de valor y las dos acciones principales |
| Regiones | Seis regiones cafeteras, cada una enlazando al catálogo filtrado |
| Destacados | Ocho cafés mejor valorados |
| Trazabilidad | Los cuatro pasos: finca, cosecha, proceso, entrega |
| Beneficios | Seis razones para comprar en la plataforma |
| Llamado final | Invitación a registrarse como productor |
| Pie de página | Cuatro secciones de enlaces más los cuatro documentos legales |

**Renderizado en servidor con revalidación cada 5 minutos.** El catálogo cambia con poca frecuencia, así que la primera carga no espera a la API (RNF-01).

**Degradación cuando no hay datos:** si la API no responde o aún no hay productos publicados —que es el estado actual, porque el módulo de catálogo llega en la fase 8— la página muestra un estado vacío explicativo en lugar de romperse. Una página de inicio que falla entera porque una sección no tiene datos es un fallo de diseño, no un caso límite.

---

## 5. Pendiente para fases siguientes

- **Fase 7:** páginas de registro, inicio de sesión y recuperación de contraseña.
- **Fase 8:** catálogo con filtros, ficha de producto, carrito y checkout.
- **Fase 9:** paneles de comprador, productor y administrador.
- **Modo oscuro:** los tokens están definidos; falta el conmutador y la persistencia de la preferencia.
- **Internacionalización:** `next-intl` está en las dependencias; los textos se extraen a archivos de traducción cuando se añada inglés (RNF-09).
