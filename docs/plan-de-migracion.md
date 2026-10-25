# Plan de migración del backend de incidencias a FastAPI

Migración de `minsa-incidencias-backend` (Node, Express 5) a esta base FastAPI con arquitectura hexagonal y DDD. El Node queda intacto como referencia y especificación. Las decisiones de arquitectura de la base están en el vault de reglas (tabla «Decisiones de arquitectura»).

## Decisiones

1. La migración vive en este repositorio, sobre `main`, en una rama y un PR por fase.
2. El contrato HTTP es idéntico al del Node para que el frontend no cambie: error `{success, statusCode, errorCode, message, timestamp, path, details?}`, validación con 400, cookie de sesión firmada compatible, cursores y cabeceras iguales. La referencia es `docs/contrato/v1.json`.
3. Cortes verticales con paridad: cada módulo se mide contra `v1.json` y contra las pruebas de integración del Node portadas.
4. Fuera de la primera entrega: el cliente Ollama, `analizar-mensaje`, la comparación de variantes, los casos de IA e `ia-poc`. `GET /incidencias/:codigo/analisis-ia` sí se migra: lee la base y datos estáticos de normas.
5. Un método no permitido responde 404 `NOT_FOUND`, como el Node.
6. Las pruebas de integración usan una base plantilla ya migrada con el esquema del bot (`TEST_TEMPLATE_DATABASE`, por defecto `bd_plantilla_desechable`); cada prueba crea su base con `CREATE DATABASE … TEMPLATE …`. Nada del esquema se copia a este repositorio.

## Fases

| Fase | Alcance | Estado |
|---|---|---|
| 0 | Preparación: contrato de referencia, base plantilla, sustitución del ejemplo por el contexto `catalogos` con `GET /v1/catalogos/plazos` | Hecha en su rama |
| 1 | Contrato de errores del Node (`success`, 400 de validación, 404 por método, los 18 códigos) | Pendiente |
| 2 | Infraestructura transversal: actor y transacción, cookie firmada, sesión, CSRF, limitador, cabeceras | Pendiente |
| 3 | `acceso` y `usuarios`, y `GET /areas` | Pendiente |
| 4 | `incidencias`, lectura y evidencias | Pendiente |
| 5 | `incidencias`, las siete acciones | Pendiente |
| 6 | `derivaciones`, `consulta_ipress`, `indicadores`, `analisis` y `filtro_corrupcion` | Pendiente |
| 7 | Archivador y clasificador | Pendiente |
| 8 | Eventos en tiempo real (SSE con LISTEN/NOTIFY) | Pendiente |
| 9 | Cierre: auditoría contra `v1.json`, documentación, variables para Infraestructura | Pendiente |

Criterio de salida de cada fase: `poe verificar` en verde, cobertura que no baja del umbral, contratos de capas sin romper, guardianas en verde y pruebas de paridad del corte en verde.

## Paridad

- Estática: comparar `v1.json` con la especificación de `/v1` de esta aplicación.
- Dinámica: validar cada respuesta real contra `v1.json` con `openapi-core` (`tests/paridad/`).
- Doble backend: Node y FastAPI contra la misma base desechable.
- Trazabilidad de las integraciones del Node portadas, con el porcentaje por fase.

## Riesgos altos

Cookie firmada compatible con `cookie-parser`, errores de triggers reconocidos por fragmento de mensaje, SQL con `?`, `::` y `%` bajo SQLAlchemy y psycopg, SAVEPOINT de `pg_trgm`, SSE y limitador por proceso, `America/Lima` en SQL, evidencias en base64, argon2 con hashes reales, y diferencias entre las expresiones regulares de JavaScript y de Python.

## Fuera de alcance por ahora

Subir a GitLab: no se hace hasta que el responsable lo pida.
