# MONK GRAIN — Instalación y despliegue

Cubre la puesta en marcha en local, el despliegue en un servidor y la operación posterior: respaldos, actualizaciones y escalado.

---

## 1. Instalación local

### Requisitos

- Docker Engine 24+ y Docker Compose v2
- Git
- 4 GB de RAM libres y ~5 GB de disco

No hace falta instalar Python ni Node.js.

### Instalación de Docker en Ubuntu y derivadas

En distribuciones basadas en Ubuntu —incluida Linux Mint— conviene fijar el nombre en clave de Ubuntu y no el de la distribución: `lsb_release -cs` devuelve el codename propio de Mint (`zena`, `virginia`…), que **no existe** en el repositorio de Docker y produce un error 404.

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl && sudo install -m 0755 -d /etc/apt/keyrings && sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Sustituye `noble` por el codename de Ubuntu que corresponda a tu versión (consúltalo con `grep UBUNTU_CODENAME /etc/os-release`):

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Para usar Docker sin `sudo`:

```bash
sudo usermod -aG docker $USER
```

El cambio de grupo **no afecta a las sesiones ya abiertas**. Cierra sesión y vuelve a entrar antes de continuar.

### Puesta en marcha

```bash
git clone <url-del-repositorio> && cd MONK-GRAIN-APP && cp .env.example .env
```

Genera la clave de firma de tokens:

```bash
openssl rand -hex 32
```

Cópiala en `SECRET_KEY` dentro de `.env`. La aplicación **rechaza arrancar** mientras conserve el valor de ejemplo.

```bash
docker compose up --build -d
```

El primer arranque tarda varios minutos: descarga las imágenes base y compila las dependencias. Las siguientes veces es cuestión de segundos.

```bash
docker compose exec backend alembic upgrade head
```

```bash
docker compose exec backend python -m app.db.seed
```

Opcionalmente, carga cafés de ejemplo para explorar la plataforma:

```bash
docker compose exec backend python -m app.db.demo_data
```

Crea la cuenta administradora. La contraseña se genera al azar y se muestra **una sola vez**:

```bash
docker compose exec backend python -m app.db.create_admin
```

### Comprobación

```bash
curl -s http://localhost:8000/health && curl -s -o /dev/null -w "web: %{http_code}\n" http://localhost:3000
```

Debe responder `{"status":"ok",...}` y `web: 200`.

---

## 2. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `SECRET_KEY conserva el valor de ejemplo` | No se generó la clave | `openssl rand -hex 32` y cópiala en `.env` |
| `permission denied ... docker.sock` | El grupo `docker` no está aplicado a la sesión | Cierra sesión y vuelve a entrar |
| El catálogo aparece vacío con HTTP 200 | El servidor de Next.js no alcanza la API | Verifica `API_INTERNAL_URL=http://backend:8000/api/v1` |
| `404` al añadir el repositorio de Docker | Se usó el codename de Mint en vez del de Ubuntu | Fija el codename de Ubuntu correspondiente |
| `relation "users" does not exist` | Falta aplicar las migraciones | `docker compose exec backend alembic upgrade head` |
| `El rol 'admin' no existe` | Faltan los datos iniciales | `docker compose exec backend python -m app.db.seed` |
| Los correos no llegan | En desarrollo no se envían de verdad | Consúltalos en http://localhost:8025 |

> El tercer caso merece atención: dentro del contenedor `web`, `localhost` es ese mismo contenedor y no el backend. El fallo se manifiesta como una página que responde 200 pero sin datos, lo cual es más difícil de detectar que un error visible.

Para ver los registros de un servicio:

```bash
docker compose logs backend --tail 50 -f
```

---

## 3. Despliegue en producción

### Diferencias respecto al entorno local

| Aspecto | Desarrollo | Producción |
|---|---|---|
| Imágenes | Etapa `development`, con recarga automática | Etapa `production`, usuario sin privilegios |
| Documentación de la API | `/docs` disponible | **Deshabilitada** |
| Nginx | No se usa | Proxy reverso con TLS |
| Correo | Mailpit, no envía nada | Servicio SMTP real |
| Almacenamiento | MinIO local | S3 o compatible |
| Base de datos | Contenedor | Servicio gestionado con respaldos |
| Registros | Consola legible | JSON estructurado |

### Variables que deben cambiar

```
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=<clave distinta de la de desarrollo>
POSTGRES_PASSWORD=<contraseña robusta>
CORS_ORIGINS=https://monkgrain.co
NEXT_PUBLIC_API_URL=https://monkgrain.co/api/v1
NEXT_PUBLIC_SITE_URL=https://monkgrain.co
PAYMENT_WEBHOOK_SECRET=<el que entregue la pasarela>
```

**La clave de producción debe ser distinta de la de desarrollo.** Reutilizarla implica que cualquiera con acceso al entorno de pruebas puede firmar tokens válidos en producción.

Los secretos no deben viajar en el repositorio ni en la imagen: úsalos mediante el gestor de secretos de la plataforma o variables inyectadas en el arranque.

### Compose de producción

El repositorio incluye `docker-compose.prod.yml`, que se superpone al de desarrollo:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Qué cambia respecto a desarrollo:

- **Imágenes de la etapa `production`**, con usuario sin privilegios y sin dependencias de desarrollo.
- **Sin volúmenes de código montados**: la imagen es inmutable y lo que se ejecuta es exactamente lo que se construyó.
- **Nginx al frente** con TLS y límite de peticiones; los puertos de PostgreSQL y Redis dejan de exponerse al exterior.
- **Mailpit y MinIO desaparecen**: en producción se usan un servicio SMTP y un almacenamiento S3 reales. Quedan tras un perfil inactivo, de modo que ni siquiera se crean.
- **`pg_stat_statements` activada** en PostgreSQL, necesaria para diagnosticar consultas lentas.
- **Redis con `maxmemory-policy noeviction`**: si se queda sin memoria preferimos que falle de forma visible antes de que descarte en silencio los contadores del limitador de peticiones.

Comprueba la configuración combinada antes de desplegar:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet && echo "configuración válida"
```

> **Detalle que conviene conocer:** Docker Compose **fusiona** `depends_on` entre archivos en lugar de reemplazarlo. Redeclararlo en el archivo de producción no elimina las dependencias del archivo base; hay que quitarlas allí. Por eso el backend no declara a MinIO como dependencia: solo lo contacta al subir un archivo, no al arrancar.

### Certificado TLS

Con Let's Encrypt:

```bash
sudo certbot certonly --standalone -d monkgrain.co -d www.monkgrain.co
```

Copia los certificados a `infra/nginx/certs/` y activa en `nginx.conf` el bloque `listen 443 ssl` junto con la redirección desde HTTP, que viene comentada.

### Migraciones en producción

Aplícalas **antes** de que arranque la versión nueva del backend, no después:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

Alembic usa DDL transaccional en PostgreSQL: si una migración falla a mitad, revierte por completo en lugar de dejar el esquema a medias.

---

## 4. Respaldos

### Copia de la base de datos

```bash
docker compose exec -T postgres pg_dump -U monkgrain -Fc monkgrain > respaldo-$(date +%F).dump
```

El formato `-Fc` está comprimido y permite restaurar tablas sueltas.

### Restauración

```bash
docker compose exec -T postgres pg_restore -U monkgrain -d monkgrain --clean --if-exists < respaldo-2026-08-13.dump
```

> `--clean` **borra los objetos existentes** antes de restaurar. Compruébalo primero en un entorno de pruebas: sobre la base equivocada, destruye los datos actuales.

### Respaldo automático diario

```bash
0 3 * * * cd /ruta/MONK-GRAIN-APP && docker compose exec -T postgres pg_dump -U monkgrain -Fc monkgrain > /respaldos/monkgrain-$(date +\%F).dump
```

Cópialos a un almacenamiento **fuera del servidor**: un respaldo que vive en la misma máquina no protege frente a la pérdida de esa máquina. Verifica periódicamente que restauran; un respaldo nunca probado no es un respaldo.

### Archivos subidos

Las imágenes y documentos viven en el almacenamiento S3, no en la base de datos. Actívale versionado y una política de retención.

---

## 5. Escalabilidad

El diseño actual —un backend, una base de datos— sostiene holgadamente el volumen de un MVP. Estas son las costuras previstas para crecer, en el orden en que conviene abordarlas:

**1. Réplica de lectura.** El catálogo es lectura intensiva. Añadir una réplica y apuntar allí los repositorios de catálogo no exige cambios en el resto.

**2. Más instancias del backend.** La aplicación no guarda estado en memoria: las sesiones viven en la base de datos y los contadores del limitador en Redis. Escalar horizontalmente es cuestión de levantar más réplicas tras Nginx.

**3. Buscador dedicado.** El índice de PostgreSQL sirve hasta decenas de miles de productos. Superado ese punto, el módulo de búsqueda se sustituye por OpenSearch detrás de la misma interfaz de repositorio.

**4. CDN para las imágenes.** Ya están fuera de la base de datos; basta con poner una CDN delante del bucket.

**5. Extracción de módulos.** `payments`, `shipments` y `notifications` son los candidatos naturales a convertirse en servicios independientes, porque su comunicación con el resto ya es por eventos y no por consultas compartidas.

**Qué vigilar antes de escalar:** tiempo de respuesta del listado del catálogo, saturación del pool de conexiones (10 por instancia, con 20 de desborde) y tasa de aciertos de la caché. Escalar sin medir suele resolver el problema equivocado.

---

## 6. Integración continua

`.github/workflows/ci.yml` se ejecuta en cada push a `main` o `develop` y en cada pull request. Un push nuevo cancela la ejecución anterior de la misma rama.

| Trabajo | Qué comprueba |
|---|---|
| **backend** | Linting, formato, tipos, migraciones y las 98 pruebas con cobertura, contra PostgreSQL y Redis reales |
| **frontend** | Tipos, linting, formato y compilación de producción |
| **docker** | Que ambas imágenes de producción construyen. Solo corre si los dos anteriores pasan |
| **security** | Dependencias con vulnerabilidades conocidas, reglas de seguridad del código y búsqueda de secretos en el historial |

Dos comprobaciones merecen mención:

- **`alembic check`** detecta el olvido más común: cambiar un modelo sin generar su migración. El código funcionaría en el equipo de quien lo escribió —su base ya tiene la columna— y fallaría al desplegarse.
- Las pruebas corren contra **PostgreSQL de verdad**, no SQLite. El esquema usa CITEXT, JSONB, ENUM nativos e índices parciales; una prueba que pase contra otro motor no demuestra nada.

La clave `SECRET_KEY` del flujo de CI es exclusiva de ese entorno y no debe coincidir con la de ningún despliegue real.

### Antes de desplegar

Lista mínima de verificación:

- [ ] La rama pasa el CI completo
- [ ] `SECRET_KEY` de producción es distinta de la de desarrollo y CI
- [ ] `APP_ENV=production` y `APP_DEBUG=false`
- [ ] `CORS_ORIGINS` contiene solo los dominios reales
- [ ] Respaldo de la base de datos hecho y **probado restaurándolo**
- [ ] Migraciones aplicadas antes de arrancar la versión nueva
- [ ] Certificado TLS vigente
- [ ] Cuenta administradora creada con contraseña guardada en un gestor

---

## 7. Operación

### Actualizar a una versión nueva

```bash
git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Haz un respaldo antes de aplicar migraciones que alteren datos.

### Supervisión

`GET /health` responde sin autenticación y sirve para el chequeo del orquestador.

Los registros salen en JSON a stdout, con un `request_id` por petición que permite seguir su rastro completo. Nunca contienen contraseñas, tokens ni datos bancarios: hay un filtro que enmascara esas claves aunque alguien registre un objeto entero por error.

Conviene alertar sobre: tasa de errores 5xx, latencia del percentil 95, pagos rechazados por firma inválida (indicio de intentos de suplantación) y conexiones de base de datos en uso.

### Activar una pasarela de pago real

1. Implementa `PaymentProvider` en `backend/app/integrations/payments/`.
2. Regístrala en `factory.py`.
3. Cambia `PAYMENT_PROVIDER` y añade sus credenciales.
4. Configura la URL del webhook en el panel del proveedor: `https://monkgrain.co/api/v1/payments/webhook`.

El módulo de pedidos no se modifica. La validación de firma ya está implementada y probada con el proveedor simulado.

**Nunca almacenes datos completos de tarjetas.** El sistema guarda únicamente referencias y tokens del proveedor, y así debe seguir.
