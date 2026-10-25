# Mediciones de calidad

Una fila por medición y por fase. Las filas no se borran. Cada umbral parte de la línea base medida y solo sube (BC12 a BC15).

Todas las filas se midieron sobre el árbol del primer commit (`91735db`); esta columna se completó en un commit posterior sin cambiar los números.

| Fecha | Commit | Fase | Medición | Comando | Resultado | Umbral | Nota |
|---|---|---|---|---|---|---|---|
| 2026-10-24 | `91735db` | 0. Línea base | Errores de tipos (`mypy --strict`, 50 archivos de `src` y `tests`) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | `91735db` | 0. Línea base | Violaciones de `ruff` con todas las reglas activas | `uv run poe lint` | 0 | 0 | Todo entra como error: el proyecto nace limpio |
| 2026-10-24 | `91735db` | 0. Línea base | Archivos sin formatear | `uv run poe format-check` | 0 de 50 | 0 | |
| 2026-10-24 | `91735db` | 0. Línea base | Contratos de capas (`import-linter`) | `uv run poe layers` | 3 cumplidos, 0 rotos | 0 rotos | Dominio puro, capas hacia adentro, kernel sin contextos |
| 2026-10-24 | `91735db` | 0. Línea base | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 94 % (56 pruebas) | 94 % | Las líneas sin cubrir son del repositorio SQL y de la sonda, que cubre la integración |
| 2026-10-24 | `91735db` | 0. Línea base | Cobertura con las pruebas de integración incluidas | `uv run pytest --cov` | 100 % (61 pruebas) | informativa | Requiere `TEST_DATABASE_URL`; no es el umbral de CI |
| 2026-10-24 | `91735db` | 0. Línea base | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 5 de 5 | todas | Incluye que `docs/esquema/nota.sql` coincide con las tablas declaradas |
| 2026-10-24 | `91735db` | 0. Línea base | Pruebas de contrato OpenAPI | `uv run poe test` | 10 de 10 | todas | Cubre éxito y errores de cada endpoint, y la salud |
| 2026-10-24 | `91735db` | 0. Línea base | Vulnerabilidades en dependencias | `uv run poe audit` | 0 | 0 | El paquete propio no está en PyPI y se omite |
| 2026-10-24 | `91735db` | 0. Línea base | Construcción de la rueda | `uv run poe build` | correcta | correcta | |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Errores de tipos (`mypy --strict`, 54 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Contratos de capas | `uv run poe layers` | 3 cumplidos, 0 rotos | 0 rotos | |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 95 % (255 pruebas) | 95 % | El umbral sube de 94 a 95 |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Cobertura con las pruebas de integración incluidas | `uv run pytest --cov` | 100 % (260 pruebas) | informativa | Requiere `TEST_DATABASE_URL` |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Pruebas de convenciones del código y de la especificación | `uv run poe test` | todas | todas | Sin comentarios, entorno solo en `config`, tamaño de archivo, dominio síncrono, `/v1` una sola vez, espejo de pruebas, 500 y ejemplos en cada operación |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Vulnerabilidades en dependencias | `uv run poe audit` | 0 | 0 | |
| 2026-10-24 | `91735db` | 1. Guardianes y correcciones | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | |
| 2026-10-24 | `91735db` | 2. Imagen y CI | Secuencia completa con imagen y CI | `uv run poe verificar` | código de salida 0 (260 pruebas, 95 %) | 0 | `mypy` 55 archivos, 0 vulnerabilidades |
| 2026-10-24 | `91735db` | 2. Imagen y CI | Imagen construida desde `git archive` del árbol, sin caché | `docker build --no-cache --pull -t migracion-fast-api:base .` | correcta | correcta | Árbol sin `.venv`, `.env` ni archivos de herramientas locales (BC34) |
| 2026-10-24 | `91735db` | 2. Imagen y CI | Contenedor contra PostgreSQL 16 | `docker run` y recorrido de la API | `healthy`, usuario `app`, 201 con `Location`, 200, 404 unificado, `/docs` 404 | todo correcto | Prueba manual, no automatizada |
| 2026-10-24 | `91735db` | 2. Imagen y CI | `/salud/listo` con la base inalcanzable | `curl` al contenedor | 503 en 0,04 s; `/salud` 200 | 503 sin esperas largas | Prueba manual del tope de conexión |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Errores de tipos (`mypy --strict`, 66 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Contratos de capas | `uv run poe layers` | 5 cumplidos, 0 rotos | 0 rotos | Se sumaron: aplicación sin frameworks, kernel sin contextos ni configuración, salud sin contextos |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 96,89 % (395 pruebas) | 96 % | El umbral sube de 95 a 96 |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 9 de 9 | todas | Incluye restricciones `CHECK` del DDL y su coincidencia con las tablas declaradas |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Errores de tipos (`mypy --strict`, 89 archivos) | `uv run poe typecheck` | 0 | 0 |  |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 |  |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Contratos de capas | `uv run poe layers` | 6 cumplidos, 0 rotos | 0 rotos | `app.nota` pasa a `app.catalogos` |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 98,15 % (599 pruebas) | 98 % | El umbral sube de 96 a 98 |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 3 de 3 | todas | Base creada desde la plantilla migrada con el esquema del bot |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Paridad con el contrato del Node | `uv run poe test` | `GET /v1/catalogos/plazos` válido contra `docs/contrato/v1.json` | todas |  |
| 2026-10-24 | `d65e3e2` | Migración 0. Preparación | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-24 | `c5109e3` | Migración 1. Errores | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 98,05 % (610 pruebas) | 98 % |  |
| 2026-10-24 | `c5109e3` | Migración 1. Errores | Paridad del contrato de errores con `ErrorPayload` del Node | `uv run poe test` | 18 códigos, estados y campos idénticos | todas | El 401 sin sesión valida contra `v1.json` |
| 2026-10-24 | `c5109e3` | Migración 1. Errores | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-24 | `d519a15` | Migración 2. Infraestructura | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 98,32 % (872 pruebas) | 98 % |  |
| 2026-10-24 | `d519a15` | Migración 2. Infraestructura | Paridad de cookie y cabeceras con el Node real | `uv run poe test` | 6 firmas, 10 lecturas y las cabeceras de helmet idénticas | todas | Vectores generados con `cookie-parser`, Express y `helmet` |
| 2026-10-24 | `d519a15` | Migración 2. Infraestructura | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 7 de 7 | todas | Incluye `app.actor` visible dentro de la transacción |
| 2026-10-24 | `d519a15` | Migración 2. Infraestructura | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 99,90 % (1838 pruebas) | 98 % | No mide `adapters/persistence/`; esos adaptadores se miden con la integración |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Cobertura total con las pruebas de integración | `uv run pytest --cov` con el `omit` sin persistencia | 99,9 % (1883 pruebas) | informativa | Requiere `TEST_DATABASE_URL` |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 45 de 45 | todas | Sesiones, usuarios, áreas, reglas de disparadores y ciclo completo de acceso |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Paridad con el contrato del Node | `uv run poe test` | 8 operaciones nuevas con el mismo `operationId`; respuestas válidas contra `v1.json` | todas | Hashes argon2 del Node verificados |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Contratos de capas | `uv run poe layers` | 9 cumplidos, 0 rotos | 0 rotos | Capas por contexto y contextos independientes entre sí |
| 2026-10-25 | `cf08887` | Migración 3. Acceso y usuarios | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-25 | `a8b39ad` | Migración 4. Incidencias (lectura) | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 99,87 % (2534 pruebas) | 98 % | No mide `adapters/persistence/` |
| 2026-10-25 | `a8b39ad` | Migración 4. Incidencias (lectura) | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 60 de 60 | todas | 15 contra casos sembrados: visibilidad por rol, filtros, cursores, conteos, evidencias, historial y por vencer |
| 2026-10-25 | `a8b39ad` | Migración 4. Incidencias (lectura) | Paridad con el contrato del Node | `uv run poe test` | 5 operaciones con el mismo `operationId`; respuestas y errores válidos contra `v1.json` | todas | El contrato detectó un identificador de evidencia que no era UUID |
| 2026-10-25 | `a8b39ad` | Migración 4. Incidencias (lectura) | Contratos de capas | `uv run poe layers` | 10 cumplidos, 0 rotos | 0 rotos | Se suma `incidencias` |
| 2026-10-25 | `a8b39ad` | Migración 4. Incidencias (lectura) | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-25 | `e4ee5e6` | Migración 5. Incidencias (acciones) | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 99,88 % (2779 pruebas) | 98 % | No mide `adapters/persistence/` |
| 2026-10-25 | `e4ee5e6` | Migración 5. Incidencias (acciones) | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 73 de 73 | todas | 13 nuevas: las siete acciones con casos sembrados, 403, 404, regla de la base (409) y dos peticiones simultáneas sobre un caso |
| 2026-10-25 | `e4ee5e6` | Migración 5. Incidencias (acciones) | Paridad con el contrato del Node | `uv run poe test` | 7 operaciones con el mismo `operationId`; respuestas felices, `enviadoAOtrans` y errores 400, 401, 403 y 404 válidos contra `v1.json` | todas | |
| 2026-10-25 | `e4ee5e6` | Migración 5. Incidencias (acciones) | Contratos de capas | `uv run poe layers` | 10 cumplidos, 0 rotos | 0 rotos | |
| 2026-10-25 | `e4ee5e6` | Migración 5. Incidencias (acciones) | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 99,93 % (4190 pruebas) | 98 % | No mide `adapters/persistence/` |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 98 de 98 | todas | 25 nuevas: derivaciones con el flujo real de OTRANS, indicadores, IPRESS y análisis guardado |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Paridad con el contrato del Node | `uv run poe test` | 15 operaciones con el mismo `operationId`; respuestas felices y errores 400, 401, 403 y 404 válidos contra `v1.json` | todas | 36 de las 37 operaciones del contrato implementadas |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Paridad del filtro de corrupción con el motor real del Node | `uv run poe test` | 835 de 835 casos con respuesta idéntica | todas | Corpus generado con el Node; incluye la vía por identidad, la zona gris, el acoso y bordes |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Tiempo del filtro con un texto adversarial de 5000 caracteres | script de una sola vez | 0,2 s (antes 7,7 s) | menos de 1 s | Índice filtrado por la segunda palabra |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Contratos de capas | `uv run poe layers` | 11 cumplidos, 0 rotos | 0 rotos | Se suma `filtro_corrupcion` |
| 2026-10-25 | `f5afa92` | Migración 6. Lecturas restantes | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades; la rueda incluye los JSON de datos |
| 2026-10-24 | `91735db` | 3. Auditoría contra el vault | Imagen reconstruida desde `git archive` y recorrido contra PostgreSQL 16 | `docker build --no-cache --pull` y `curl` | 201 con `Location`, 422 sin repetir lo enviado, 413 a 150 KB, cabeceras de seguridad, CORS solo del origen permitido, `/docs` 404 en producción, base caída: `/salud/listo` 503 y `/v1/notas` 503 en 15 ms | todo correcto | Prueba manual, no automatizada |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Errores de tipos (`mypy --strict`, 92 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Contratos de capas | `uv run poe layers` | 6 cumplidos, 0 rotos | 0 rotos | Se sumó: las carpetas puras (`constants`, `enums`, `errors`) no dependen de capas ni de frameworks |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 97,32 % (651 pruebas) | 97 % | El umbral sube de 96 a 97 |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 9 de 9 | todas | |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Pruebas guardianas de estructura (BA36, BA56, BA62, BA67) | `uv run poe test` | cada una falla ante su violación | todas | Comprobado introduciendo a propósito una clase de error duplicada, dos enums, un `re.compile` y un número de regla sueltos |
| 2026-10-24 | `91735db` | 4. Carpetas puras y reglas del vault | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-24 | `fcb1ccf` | 5. Hooks y CI simulado | Secuencia completa | `uv run poe verificar` | código de salida 0 (673 pruebas, 97,33 %) | 0 | `mypy` 94 archivos, 0 vulnerabilidades |
| 2026-10-24 | `fcb1ccf` | 5. Hooks y CI simulado | Pre-commit real (`git commit`) | `lefthook` | formato, lint, tipos y pruebas pasan | todos | Falló una vez por las comillas de `-m "not integration"`; corregido con una tarea de `poe` y una guardiana |
| 2026-10-24 | `fcb1ccf` | 5. Hooks y CI simulado | Pre-push real (`git push` a un remoto local desechable) | `lefthook` | con base pasa; sin `TEST_DATABASE_URL` se bloquea con un solo mensaje; con `LEFTHOOK_EXCLUDE=integracion` pasa | los tres | Prueba manual, no automatizada |
| 2026-10-24 | `fcb1ccf` | 5. Hooks y CI simulado | CI en contenedor Linux limpio con `CI=true` | `docker run python:3.14.7-slim-bookworm` y `poe verificar` | código de salida 0 (673 pruebas, 97,33 %) | 0 | Prueba manual; el árbol entra por `tar` para conservar los modos de git |
| 2026-10-24 | `2e4edc2` | 6. Hooks definitivos | Pre-push real con base disponible | `git push` y `lefthook` | `integracion` 5,8 s y `verificar` 35 s, ambos pasan | pasan | Prueba manual contra un remoto local desechable |
| 2026-10-24 | `2e4edc2` | 6. Hooks definitivos | Pre-push real sin `TEST_DATABASE_URL` | `git push` y `lefthook` | bloqueado en 4,5 s con `verificar (skip)` y un solo mensaje | bloquea sin correr `verificar` | Antes tardaba 28 s: `fail_fast` no existe en `lefthook`; la opción real es `piped` |
| 2026-10-24 | `2e4edc2` | 6. Hooks definitivos | Pruebas de los hooks (`tests/convenciones/test_hooks.py`) | `uv run poe test` | 15 de 15; fallan si vuelve `fail_fast` o una comilla | todas | Comprobado reintroduciendo cada defecto |

## Exclusiones de cobertura

| Archivo | Motivo |
|---|---|
| `src/app/main.py` y `src/app/__main__.py` | Arranque: leen el entorno y arman el contenedor real (BC21) |
| `src/app/**/ports.py` | Solo declara protocolos sin lógica; `mypy --strict` comprueba que los adaptadores y los falsos los cumplen |

## Mediciones periódicas pendientes

No entran en la línea base. Se suman de a una cuando el proyecto las pida (BC27 a BC31), cada una con su script y su fila.

| Medición | Herramienta propuesta | Regla |
|---|---|---|
| Duplicación | `jscpd` o equivalente en Python, bloques de 6 líneas o más | BC29 |
| Mutación en módulos críticos | `mutmut` o `cosmic-ray` | BC30 |
| Código sin uso | `vulture` | BC28 |
