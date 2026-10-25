# Mediciones de calidad

Una fila por medición y por fase. Las filas no se borran. Cada umbral parte de la línea base medida y solo sube (BC12 a BC15).

El repositorio todavía no tiene commits: la columna Commit dice `sin commit` hasta el primer commit y se completa en ese momento, sin cambiar los números.

| Fecha | Commit | Fase | Medición | Comando | Resultado | Umbral | Nota |
|---|---|---|---|---|---|---|---|
| 2026-10-24 | sin commit | 0. Línea base | Errores de tipos (`mypy --strict`, 50 archivos de `src` y `tests`) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | sin commit | 0. Línea base | Violaciones de `ruff` con todas las reglas activas | `uv run poe lint` | 0 | 0 | Todo entra como error: el proyecto nace limpio |
| 2026-10-24 | sin commit | 0. Línea base | Archivos sin formatear | `uv run poe format-check` | 0 de 50 | 0 | |
| 2026-10-24 | sin commit | 0. Línea base | Contratos de capas (`import-linter`) | `uv run poe layers` | 3 cumplidos, 0 rotos | 0 rotos | Dominio puro, capas hacia adentro, kernel sin contextos |
| 2026-10-24 | sin commit | 0. Línea base | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 94 % (56 pruebas) | 94 % | Las líneas sin cubrir son del repositorio SQL y de la sonda, que cubre la integración |
| 2026-10-24 | sin commit | 0. Línea base | Cobertura con las pruebas de integración incluidas | `uv run pytest --cov` | 100 % (61 pruebas) | informativa | Requiere `TEST_DATABASE_URL`; no es el umbral de CI |
| 2026-10-24 | sin commit | 0. Línea base | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 5 de 5 | todas | Incluye que `docs/esquema/nota.sql` coincide con las tablas declaradas |
| 2026-10-24 | sin commit | 0. Línea base | Pruebas de contrato OpenAPI | `uv run poe test` | 10 de 10 | todas | Cubre éxito y errores de cada endpoint, y la salud |
| 2026-10-24 | sin commit | 0. Línea base | Vulnerabilidades en dependencias | `uv run poe audit` | 0 | 0 | El paquete propio no está en PyPI y se omite |
| 2026-10-24 | sin commit | 0. Línea base | Construcción de la rueda | `uv run poe build` | correcta | correcta | |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Errores de tipos (`mypy --strict`, 54 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Contratos de capas | `uv run poe layers` | 3 cumplidos, 0 rotos | 0 rotos | |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 95 % (255 pruebas) | 95 % | El umbral sube de 94 a 95 |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Cobertura con las pruebas de integración incluidas | `uv run pytest --cov` | 100 % (260 pruebas) | informativa | Requiere `TEST_DATABASE_URL` |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Pruebas de convenciones del código y de la especificación | `uv run poe test` | todas | todas | Sin comentarios, entorno solo en `config`, tamaño de archivo, dominio síncrono, `/v1` una sola vez, espejo de pruebas, 500 y ejemplos en cada operación |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Vulnerabilidades en dependencias | `uv run poe audit` | 0 | 0 | |
| 2026-10-24 | sin commit | 1. Guardianes y correcciones | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | |
| 2026-10-24 | sin commit | 2. Imagen y CI | Secuencia completa con imagen y CI | `uv run poe verificar` | código de salida 0 (260 pruebas, 95 %) | 0 | `mypy` 55 archivos, 0 vulnerabilidades |
| 2026-10-24 | sin commit | 2. Imagen y CI | Imagen construida desde `git archive` del árbol, sin caché | `docker build --no-cache --pull -t migracion-fast-api:base .` | correcta | correcta | Árbol sin `.venv`, `.env` ni archivos de herramientas locales (BC34) |
| 2026-10-24 | sin commit | 2. Imagen y CI | Contenedor contra PostgreSQL 16 | `docker run` y recorrido de la API | `healthy`, usuario `app`, 201 con `Location`, 200, 404 unificado, `/docs` 404 | todo correcto | Prueba manual, no automatizada |
| 2026-10-24 | sin commit | 2. Imagen y CI | `/salud/listo` con la base inalcanzable | `curl` al contenedor | 503 en 0,04 s; `/salud` 200 | 503 sin esperas largas | Prueba manual del tope de conexión |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Errores de tipos (`mypy --strict`, 66 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Contratos de capas | `uv run poe layers` | 5 cumplidos, 0 rotos | 0 rotos | Se sumaron: aplicación sin frameworks, kernel sin contextos ni configuración, salud sin contextos |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 96,89 % (395 pruebas) | 96 % | El umbral sube de 95 a 96 |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 9 de 9 | todas | Incluye restricciones `CHECK` del DDL y su coincidencia con las tablas declaradas |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |
| 2026-10-24 | sin commit | 3. Auditoría contra el vault | Imagen reconstruida desde `git archive` y recorrido contra PostgreSQL 16 | `docker build --no-cache --pull` y `curl` | 201 con `Location`, 422 sin repetir lo enviado, 413 a 150 KB, cabeceras de seguridad, CORS solo del origen permitido, `/docs` 404 en producción, base caída: `/salud/listo` 503 y `/v1/notas` 503 en 15 ms | todo correcto | Prueba manual, no automatizada |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Errores de tipos (`mypy --strict`, 92 archivos) | `uv run poe typecheck` | 0 | 0 | |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Violaciones de `ruff` con todas las reglas | `uv run poe lint` | 0 | 0 | |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Contratos de capas | `uv run poe layers` | 6 cumplidos, 0 rotos | 0 rotos | Se sumó: las carpetas puras (`constants`, `enums`, `errors`) no dependen de capas ni de frameworks |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Cobertura de líneas y ramas, pruebas unitarias | `uv run poe test-coverage` | 97,32 % (651 pruebas) | 97 % | El umbral sube de 96 a 97 |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Pruebas contra la base (PostgreSQL 16) | `uv run poe test-integration` | 9 de 9 | todas | |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Pruebas guardianas de estructura (BA36, BA56, BA62, BA67) | `uv run poe test` | cada una falla ante su violación | todas | Comprobado introduciendo a propósito una clase de error duplicada, dos enums, un `re.compile` y un número de regla sueltos |
| 2026-10-24 | sin commit | 4. Carpetas puras y reglas del vault | Secuencia completa | `uv run poe verificar` | código de salida 0 | 0 | 0 vulnerabilidades |

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
