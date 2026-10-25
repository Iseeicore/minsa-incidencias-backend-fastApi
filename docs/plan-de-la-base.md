# Plan de la base FastAPI

Base genérica de un backend FastAPI con arquitectura hexagonal y DDD, construida con las reglas del vault del backend (BA, BT, BC). El contexto `nota` es un ejemplo para reemplazar al arrancar un proyecto real.

## Decisiones

| Tema | Decisión | Reglas |
|---|---|---|
| Python y gestor | Python 3.14.7 con `uv`; `uv.lock` versionado | BC35 |
| Arquitectura | Hexagonal con DDD; el dominio es puro y los puertos los define el núcleo | BA12, BA13, BA24 |
| Idioma de los nombres | Dominio en español (`nota`, `codigo`), técnico en inglés (`repository`, `settings`) | BA139 |
| Tipos | `mypy --strict` con el plugin de pydantic | BC02, BC03 |
| Lint y formato | `ruff` con todas las reglas, una sola herramienta | BC17, BC18 |
| Capas | `import-linter`, una sola herramienta | BC19 |
| Acceso a datos | SQLAlchemy Core async con `psycopg` 3; SQL sin ORM; el esquema es del dueño de la base | BA03 |
| Configuración | `pydantic-settings` en un solo módulo; falla al arrancar | BC05 |
| Hora | Puerto `Clock` inyectado | BA23 |
| API | `/v1/notas`; salud en `/salud` y `/salud/listo` sin versión | BA154, BC08 |
| Tareas | `poethepoet`; `poe verificar` encadena el núcleo | BC13, BC23 |
| Hooks | `lefthook` | BC24 |
| Pruebas | Carpeta espejo `tests/`; falsos en memoria; integración con `TEST_DATABASE_URL` | BT01, BT09, BT16 |
| CI | GitHub Actions y GitLab CI, los dos con `poe verificar` | BC23 |
| Documentación | En español | |

## Hecho

- Dominio, aplicación, HTTP y persistencia del contexto `nota`.
- Errores con formato único, salud, logs estructurados y configuración tipada.
- Pool de conexiones configurable por entorno (`DB_POOL_MAX`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`, `DB_STATEMENT_TIMEOUT_MS`).
- Pruebas unitarias, de contrato OpenAPI y de integración contra PostgreSQL 16.
- Línea base en `docs/calidad/mediciones.md`.

## Pendiente de la fase

| # | Pieza | Regla |
|---|---|---|
| 1 | Hecho: `lefthook.yml` con pre-commit (`ruff`, `mypy`, pruebas) y pre-push (`poe verificar`) | BC24 |
| 2 | Hecho: pruebas de convenciones del código y de la especificación | BT13, BA19 |
| 3 | Hecho: `Dockerfile` multietapa con imagen fijada, usuario sin privilegios y `HEALTHCHECK` a `/salud` | BC32, BC33 |
| 4 | Hecho: imagen verificada desde `git archive` con `docker build --no-cache --pull` | BC34 |
| 5 | Hecho: `.github/workflows/ci.yml` y `.gitlab-ci.yml` con `poe verificar`, sin caché; falta correrlos en GitHub y GitLab, que exige subir el repo | BC23 |
| 6 | Hecho: README mínimo | BC37 |
| 7 | Hecho: primer commit (`91735db`) y columna Commit de las mediciones | BC12 |
| 9 | Hecho: carpetas puras (`constants`, `enums`, `errors`), un enum y un error por archivo, textos y regex aislados, con pruebas guardianas | BA36, BA56, BA62, BA65, BA67 |
| 10 | Hecho: hooks verificados con un commit y un push reales, CI simulado en Linux limpio y `HEAD` en la salud | BC24, BT16 |
| 8 | Pendientes de la auditoría, diferidos a propósito: clave de idempotencia en `POST` (BA151), fijar `actions/checkout` por SHA, entidad devuelta al controlador (BA02) | BA151, BA02 |

## Fuera de la base

Mutación, duplicación y código sin uso se miden al cerrar una fase (BC28 a BC30). Autenticación, sesiones y un segundo contexto se agregan cuando el proyecto real los pida; el contrato "un módulo no importa de otro" (BA16) se suma con el segundo contexto.
