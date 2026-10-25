# migracion-fast-api

Base de un backend FastAPI con arquitectura hexagonal y DDD, con el mismo contrato de variables de entorno que el backend de incidencias. El contexto `nota` es un ejemplo para reemplazar al arrancar un proyecto real.

## Requisitos

- Python 3.14.7 y `uv` 0.13.5.
- PostgreSQL 16. El esquema lo crea su dueño; el DDL del ejemplo está en `docs/esquema/nota.sql`. Este servicio no migra.

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

Hoy el código consume `NODE_ENV`, `PORT`, `LOG_LEVEL`, `DATABASE_URL`, `CORS_ORIGINS`, `TRUST_PROXY` y las cuatro `DB_*`. El resto se lee y se valida, pero todavía no tiene consumidor: se conectan al migrar sesiones, limitador, archivado y clasificador.

## Pruebas contra la base y hooks

Las pruebas de integración necesitan `TEST_DATABASE_URL`: una base PostgreSQL 16 desechable donde se puedan crear bases. El pre-push las corre (BT16), así que sin esa variable el push se detiene con un mensaje claro.

```
docker run -d --name pg-pruebas -e POSTGRES_USER=pruebas -e POSTGRES_PASSWORD=CLAVE -p 127.0.0.1:55432:5432 postgres:16
TEST_DATABASE_URL=postgresql://pruebas:CLAVE@127.0.0.1:55432/postgres uv run poe test-integration
```

Para omitir esa parte del pre-push de forma consciente: `LEFTHOOK_EXCLUDE=integracion git push`.

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
  <contexto>/        un contexto delimitado (hoy: nota)
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
  esquema/           DDL de referencia del contexto de ejemplo
  plan-de-la-base.md decisiones, hecho y pendiente de la base
```

- **Dependencias hacia adentro:** `adapters` importa `application`, y `application` importa `domain`. Nunca al revés. Lo vigila `import-linter`.
- **Un contexto no importa de otro** ni de la implementación de otro; lo compartido va a `shared/`.
- **Carpetas puras:** `constants/`, `enums/` y `errors/` no importan capas ni frameworks (`import-linter`). Los números de regla van en `constants/`; las expresiones regulares, solo en `nota/domain/patrones.py` (se arma con datos del dominio); una prueba lo vigila.
- **Un archivo, una prueba:** `src/app/<ruta>/x.py` tiene su prueba en `tests/<ruta>/test_x.py`. Las excepciones (archivos de solo constantes, protocolos o arranque) están declaradas con su motivo en `tests/convenciones/test_codigo.py`.
- **Nombres:** el dominio va en español (`nota`, `codigo`) y lo técnico en inglés (`repository`, `settings`).
- **Contexto nuevo:** se crea `src/app/<contexto>/{domain,application,adapters}`, su espejo en `tests/` y se monta su router en `composition.py`.

Los endpoints se documentan en la especificación OpenAPI de `/v1` (visible fuera de producción).
