# migracion-fast-api

Migración del backend de incidencias a FastAPI con arquitectura hexagonal y DDD, con el mismo contrato de variables de entorno y de API que el backend Node. El avance por fases está en `docs/plan-de-migracion.md`.

## Requisitos

- Python 3.14.7 y `uv` 0.13.5.
- PostgreSQL 16. El esquema es del bot de citas (`prisma/migrations` y `prisma/sql` de `minsa-citas-whatsapp-bot`). Este servicio no migra.

## Instalar, levantar y verificar

```
uv sync --locked
uv run poe hooks
uv run python -m app
uv run poe verificar
```

Un único proceso: el API. Con Docker: `docker build -t migracion-fast-api .`.

## Variables de entorno

Se leen solo en `src/app/config/settings.py`. Si falta una obligatoria o un valor no cumple el contrato, el servicio no arranca. `.env.example` lista todas.

| Variable | Obligatoria | Valor por defecto | Para qué sirve |
|---|---|---|---|
| `NODE_ENV` | No | `production` | `development`, `test` o `production`. Fuera de producción se sirven `/docs`, `/redoc` y `/openapi.json` |
| `PORT` | No | `3033` | Puerto del servicio |
| `LOG_LEVEL` | No | `info` | `fatal`, `error`, `warn`, `info`, `debug`, `trace` o `silent` |
| `DATABASE_URL` | Sí | | URL de PostgreSQL (`postgresql://USUARIO:CLAVE@HOST:PUERTO/BASE`) |
| `CORS_ORIGINS` | No | vacío | Orígenes permitidos separados por coma, cada uno con esquema, dominio y puerto, sin ruta ni comodín |
| `TRUST_PROXY` | No | `false` | `true` si hay un balanceador o proxy delante |
| `DB_POOL_MAX` | No | `10` | Conexiones máximas del pool |
| `DB_IDLE_TIMEOUT_MS` | No | `30000` | Antigüedad máxima de una conexión antes de reciclarla (aproximación de la inactividad del pool de Node) |
| `DB_CONNECTION_TIMEOUT_MS` | No | `5000` | Espera por una conexión y tope para conectar |
| `DB_STATEMENT_TIMEOUT_MS` | No | `15000` | Duración máxima de una consulta |
| `COOKIE_SECRET` | Sí | | Secreto de sesión, 32 caracteres como mínimo |
| `COOKIE_SECRET_PREVIOUS` | No | vacío | Secretos anteriores separados por coma, 32 caracteres como mínimo cada uno |
| `CLASIFICADOR_MODO` | No | `externo` | `externo` o `sondeo` |
| `SESSION_IDLE_MINUTES` | No | `30` | Inactividad máxima de una sesión |
| `SESSION_ABSOLUTE_HOURS` | No | `8` | Duración máxima de una sesión |
| `VIGENCIA_RESOLUCION_DIAS` | No | `3` | Días de vigencia de una resolución |
| `PLAZO_AVISO_HORAS` | No | `24` | Horas de aviso antes de un plazo |
| `ARCHIVADO_INTERVAL_SECONDS` | No | `60` | Segundos entre corridas del archivado |
| `ARCHIVADO_LOTE` | No | `1000` | Casos por corrida del archivado |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `300` | Ventana del limitador general |
| `RATE_LIMIT_AUTH_CAPACITY` | No | `300` | Peticiones por ventana con sesión |
| `RATE_LIMIT_ANON_CAPACITY` | No | `100` | Peticiones por ventana sin sesión |
| `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | No | `900` | Ventana del limitador de inicio de sesión |
| `RATE_LIMIT_LOGIN_CAPACITY` | No | `5` | Intentos por ventana y usuario |
| `RATE_LIMIT_LOGIN_IP_CAPACITY` | No | `30` | Intentos por ventana y dirección IP |

Detrás de un balanceador, `TRUST_PROXY=true` activa la lectura de `X-Forwarded-*`, pero `uvicorn` solo confía en las direcciones de la variable `FORWARDED_ALLOW_IPS` (por defecto `127.0.0.1`): define con ella las IP del proxy; no se usa `*`.

Límites de entrada: cuerpo de hasta 100 KiB, título de hasta 120 caracteres y contenido de hasta 10 000.

## Procesos de fondo

El archivador corre dentro del servidor: archiva de inmediato y luego cada `ARCHIVADO_INTERVAL_SECONDS`, `ARCHIVADO_LOTE` casos por vez y con `VIGENCIA_RESOLUCION_DIAS` para lo resuelto. Toma un candado de PostgreSQL en cada pasada, así que si hay más de una instancia solo una archiva a la vez.

El clasificador toma de la cola los casos registrados sin categoría de la IA, del más antiguo al más nuevo, y escribe en una sola transacción el análisis y la categoría. Un caso que falla tres veces se deja fuera hasta reiniciar. Hay dos formas de correrlo:

- `CLASIFICADOR_MODO=sondeo`: dentro del servidor, cada 5 segundos.
- `CLASIFICADOR_MODO=externo` (por defecto): el servidor no lo ejecuta. Se corre aparte con `python -m app clasificador`, o con `python -m app clasificador --una-vez` para una sola pasada. Se recomienda un solo proceso clasificador por base.

Los dos cierran ordenadamente: esperan al ciclo en curso antes de soltar la conexión.

## Pruebas contra la base y hooks

Las pruebas de integración necesitan dos cosas: `TEST_DATABASE_URL`, un servidor PostgreSQL 16 desechable donde el usuario pueda crear bases, y una **base plantilla** ya migrada con el esquema del bot, cuyo nombre (por defecto `bd_plantilla_desechable`, o el de `TEST_TEMPLATE_DATABASE`) debe terminar en `_desechable`, `_dev` o `_local`. Cada prueba crea su propia base con `CREATE DATABASE … TEMPLATE …` y la borra al terminar. El pre-push las corre (BT16), así que sin `TEST_DATABASE_URL` el push se detiene con un mensaje claro.

```
docker run -d --name pg-pruebas -e POSTGRES_USER=pruebas -e POSTGRES_PASSWORD=CLAVE -p 127.0.0.1:55432:5432 postgres:16
BOT_PRISMA_DIR=RUTA/minsa-citas-whatsapp-bot/prisma TEST_DATABASE_URL=postgresql://pruebas:CLAVE@127.0.0.1:55432/postgres uv run poe plantilla
TEST_DATABASE_URL=postgresql://pruebas:CLAVE@127.0.0.1:55432/postgres uv run poe test-integration
```

Para omitir esa parte del pre-push de forma consciente: `LEFTHOOK_EXCLUDE=integracion git push`.

Si falta la variable, las pruebas de integración terminan con un único mensaje y código 2, y el hook se detiene en el primer fallo.

Los comandos de `lefthook.yml` son siempre tareas de `poe` y no llevan comillas: en Windows `lefthook` ejecuta `sh -c "…"` sin escapar las comillas internas y el comando se rompe. Una prueba lo vigila.

## Estructura de carpetas

```
src/app/
  main.py            arranque real: arma el contenedor con los adaptadores
  __main__.py        punto de entrada del contenedor (python -m app)
  composition.py     raíz de composición: contenedor, CORS y montaje de /v1
  config/            única lectura del entorno (settings.py)
  constants/         constantes sin lógica: límites, valores por defecto del entorno, HTTP, base y textos de error
  enums/             un enum por archivo
  errors/            una clase de error por archivo, con el nombre del archivo igual al de la clase
  health/            rutas /salud y /salud/listo
  shared/            núcleo compartido sin negocio: errores, reloj, logs, base, errores HTTP
  <contexto>/        un contexto delimitado (hoy: catalogos, acceso, usuarios, incidencias)
    domain/          reglas de negocio puras y síncronas; sin frameworks ni drivers (errors/ propios, constantes y patrones)
    application/     casos de uso y puertos (protocolos); no conocen HTTP ni SQL
    adapters/
      http/          router y esquemas de la API
      persistence/   tablas y repositorio SQL
tests/               espejo exacto de src/app/
  helpers/           builders, falsos en memoria y ayudantes de contrato
  convenciones/      pruebas que hacen cumplir las reglas del proyecto
docs/
  calidad/           mediciones.md con la línea base y los umbrales
  contrato/          v1.json y salud.json del backend Node, y su origen
  plan-de-migracion.md fases de la migración y su estado
```

- **Dependencias hacia adentro:** `adapters` importa `application`, y `application` importa `domain`. Nunca al revés. Lo vigila `import-linter`.
- **Un contexto no importa de otro** ni de la implementación de otro; lo compartido va a `shared/`.
- **Carpetas puras:** `constants/`, `enums/` y `errors/` no importan capas ni frameworks (`import-linter`). Los números de regla van en `constants/`; las expresiones regulares, solo en archivos de patrones (`<contexto>/domain/patrones.py`); una prueba lo vigila.
- **Un archivo, una prueba:** `src/app/<ruta>/x.py` tiene su prueba en `tests/<ruta>/test_x.py`. Las excepciones (archivos de solo constantes, protocolos o arranque) están declaradas con su motivo en `tests/convenciones/test_codigo.py`.
- **Nombres:** el dominio va en español (`catalogos`, `acceso`, `usuarios`, `plazo`) y lo técnico en inglés (`repository`, `settings`).
- **Contexto nuevo:** se crea `src/app/<contexto>/{domain,application,adapters}`, su espejo en `tests/` y se monta su router en `composition.py`.

Los endpoints se documentan en la especificación OpenAPI de `/v1` (visible fuera de producción).
