# Plan de migración del backend de incidencias a FastAPI

Migración de `minsa-incidencias-backend` (Node, Express 5) a esta base FastAPI con arquitectura hexagonal y DDD. El Node queda intacto como referencia y especificación. Las decisiones de arquitectura de la base están en el vault de reglas (tabla «Decisiones de arquitectura»).

## Decisiones

1. La migración vive en este repositorio, sobre `main`, en una rama y un PR por fase.
2. El contrato HTTP es idéntico al del Node para que el frontend no cambie: error `{success, statusCode, errorCode, message, timestamp, path, details?}`, validación con 400, cookie de sesión firmada compatible, cursores y cabeceras iguales. La referencia es `docs/contrato/v1.json`.
3. Cortes verticales con paridad: cada módulo se mide contra `v1.json` y contra las pruebas de integración del Node portadas.
4. Fuera de la primera entrega: el cliente Ollama, `analizar-mensaje`, la comparación de variantes, los casos de IA e `ia-poc`. `GET /incidencias/:codigo/analisis-ia` sí se migra: lee la base y datos estáticos de normas.
5. Un método no permitido responde 404 `NOT_FOUND`, como el Node.
6. Una falla de la base en una ruta de negocio responde 500 `INTERNAL_ERROR`, como el Node; el 503 `SERVICE_UNAVAILABLE` queda solo para `/salud/listo`. No existe 504.
7. Un JSON mal formado responde 400 `VALIDATION_FAILED` sin `details`. Los `details` de un campo inválido usan la ruta del campo sin el prefijo `body`, `query` o `path`; los mensajes son los de Pydantic, no los de zod (diferencia aceptada).
8. La cookie de sesión es compatible byte a byte con `cookie-parser` y `res.cookie` de Express; los vectores salen del Node real (`tests/fixtures/vectores_node.json`, generados con la pila de `minsa-incidencias-backend`). Las cabeceras de seguridad son las de `helmet` 8.3.0, más `Cache-Control: no-store`; la política de contenido se omite en `/docs`, `/redoc` y `/openapi.json`.
9. La sesión se resuelve por un puerto (`SessionResolver`). Hasta la Fase 3 el resolvedor de producción no reconoce ninguna sesión, así que toda cookie firmada y bien formada responde `INVALID_SESSION`.
10. El limitador es por proceso (cubeta de fichas con el mismo cálculo del Node), con barrido cada 60 s. Con `TRUST_PROXY=true` la IP es el primer valor de `X-Forwarded-For`. Los límites de login (por correo y por IP) llegan con la Fase 3 porque leen el cuerpo. El control de conexiones de tiempo real (`iniciarVerificacion`/`liberar`) llega con la Fase 8.
11. Los hashes de contraseña que ya existen en la base los generó el Node con argon2id y ordenan los parámetros como `m,p,t`; la biblioteca de Python los exige como `m,t,p`. `shared/argon2_hash.py` los reordena antes de verificar, y una prueba usa hashes generados por el Node real (`tests/fixtures/hashes_argon2_node.json`). Los hashes nuevos salen en el orden estándar y el Node también los verifica.
12. Los límites de login (5 por correo y 30 por IP en 900 s) corren antes de validar el cuerpo, como en el Node, y se cuentan con el correo recortado y en minúsculas.
13. El permiso por vista (`require_vista`) y la matriz de roles viven en el núcleo (`shared/permisos.py`). Solo trae lo que usan `acceso`, `usuarios` y `GET /areas`; las acciones sobre incidencias y las tarjetas llegan con sus fases.
14. Las reglas de los disparadores se traducen por fragmento de mensaje a 409 (conflicto) o 422 (regla corregible) en `shared/reglas_de_la_base.py`. La tabla completa (33 reglas) ya está cargada aunque las de incidencias se ejercitan en la Fase 5.
15. La cobertura mínima de las pruebas unitarias (98 %) no mide `adapters/persistence/`: esos adaptadores se miden con las pruebas de integración contra el esquema del bot. Con ambas tandas la cobertura total es 99,9 %.
16. Fuera de esta fase queda el cierre de conexiones en vivo al desactivar o cambiar a un usuario (`seguimiento.invalidarUsuario` del Node); llega con la Fase 8.
17. Las consultas de `incidencias` se arman con fragmentos fijos y valores siempre como parámetros enlazados (`ParametrosSql`), igual que el Node arma su SQL dinámico; solo se agregan las condiciones de los filtros recibidos para que el plan de consulta sea el mismo. Todo valor lleva `CAST(... AS tipo)` porque el `::` pegado a un marcador no se reconoce bajo SQLAlchemy.
18. Los cursores son los del Node: base64url de `fechaISO|id` (listado) o `por-vencer|vence-en|fechaISO|id` (por vencer), con la fecha en UTC y milisegundos. Las fechas con microsegundos se truncan a milisegundos al codificar, como hace el Node al leerlas.
19. La matriz de acciones por rol (confirmar, corregir, derivar, tomar, resolver, archivar, reabrir) ya vive en `shared/permisos.py` porque el detalle y el listado informan las acciones permitidas; las siete acciones HTTP llegan con la Fase 5. La visibilidad de `consulta_ipress` y de derivaciones (`VisibilidadConsulta`) llega con la Fase 6.
20. La imagen de una evidencia se entrega solo si la ruta es un data URI `data:image/{jpeg|png|webp};base64,` con base64 canónico; si no, responde 404 `EVIDENCIA_NO_DISPONIBLE`. Sus cabeceras (`Cache-Control: private, no-store`, CSP `default-src 'none'; sandbox`) reemplazan a las generales.
21. Las pruebas de integración usan una base plantilla ya migrada con el esquema del bot (`TEST_TEMPLATE_DATABASE`, por defecto `bd_plantilla_desechable`); cada prueba crea su base con `CREATE DATABASE … TEMPLATE …`. Nada del esquema se copia a este repositorio.

22. Cada acción sobre un caso es un objeto de la capa de aplicación (`Confirmar`, `Corregir`, `Derivar`, `Tomar`, `Resolver`, `Archivar`, `Reabrir`) que la capa HTTP arma desde un cuerpo ya validado. El caso de uso `EjecutarAccion` es el mismo para las siete: abre la transacción con el actor `usuario:{correo}`, bloquea el caso con `FOR UPDATE OF i`, comprueba que la acción esté entre las permitidas para los roles de la sesión y la aplica. Así no existe el 400 «faltan datos» del Node: un campo obligatorio ausente ya falló en el esquema de la petición.
23. Lo que el Node valida dos veces (zod y servicio) aquí se valida en el esquema de la petición, con los mismos límites y mensajes de longitud (10 a 2000 o 4000 caracteres, recortados). Un campo opcional enviado como `null` responde 400, como en zod. Se conserva en el servicio la regla que el esquema no cubre: OTRANS que devuelve un caso a su origen exige la descripción de la derivación.
24. Si tras la acción el caso ya no es visible para quien la hizo, se responde sin releerlo: una corrección a denuncia por corrupción responde `{codigo, enviadoAOtrans: true}`; cualquier otra corrección, el mensaje con la etiqueta de la categoría y `caso: null`; el resto, su mensaje y `caso: null`.
25. Los disparadores de la base siguen siendo la última palabra: por ejemplo, reabrir un caso archivado por vigencia responde 409 con el mensaje de la regla, no 422 ni 403. Una prueba de integración lo fija contra el esquema del bot.
26. Dos peticiones simultáneas sobre el mismo caso se serializan por el bloqueo de fila: la segunda ve el estado nuevo y recibe 403 «no puedes…». Lo comprueba una prueba con dos tareas `asyncio` sobre la misma base.

27. `derivaciones`, `indicadores` y `consulta_ipress` viven dentro de `incidencias` y no como contextos aparte, que era lo previsto en el plan inicial: son lecturas del mismo agregado con otra visibilidad y reutilizan el listado, los conteos, el detalle y la evidencia. Como contextos separados, el contrato de independencia les prohibiría esa reutilización. La visibilidad pasó a ser `Visibilidad = VisibilidadOperativa | VisibilidadDeDerivaciones | VisibilidadDeIpress`, y los casos de uso existentes aceptan una explícita.
28. Con una visibilidad explícita (seguimiento de derivaciones y consulta de IPRESS) los casos salen sin acciones de gestión, como en el Node, que en ese caso no pasa la sesión a quien arma el resumen.
29. En la consulta de IPRESS el código de la ruta se valida después de la consulta: un `periodo` o un filtro inválido responde 400 antes que el 404 por un RENIPRESS inválido, igual que el Node. El filtro `establecimiento` se valida pero se ignora, porque la ruta ya fija la IPRESS.
30. El análisis guardado se lee de forma tolerante, campo a campo, como los `.catch` de zod: lo inválido toma su valor por defecto. La ficha de derivación se tipa y se descarta si no tiene la forma esperada, mientras que el Node la devuelve sin validar. Los 29 fragmentos de normas se generaron desde el Node y se comprobó que son idénticos.
31. `filtro_corrupcion` es un contexto propio y puro. Su léxico, sus clases, el catálogo de 37 entidades y las 18 ubicaciones son JSON generado desde el Node en `constants/datos/` y viajan dentro de la rueda. El motor es síncrono: la ruta es una función normal que FastAPI ejecuta en su grupo de hilos.
32. Equivalencias con JavaScript sin usar `re`: el recorte usa los blancos de `String.prototype.trim`, la longitud se cuenta en unidades UTF-16, `\p{L}`, `\p{N}` y `\p{M}` salen de `unicodedata`, `Math.round` es `floor(x + 0,5)` y los nombres propios se buscan con un recorrido que imita la expresión del Node.
33. El índice de coincidencias filtra los candidatos por la segunda palabra y conserva el orden: un texto de 5000 caracteres que repite «si» pasó de 7,7 s a 0,2 s sin cambiar ningún resultado.
34. Corpus de oro del filtro: `tests/fixtures/corpus_corrupcion_node.json` guarda 835 casos (texto, contexto, `pesoIa` y respuesta) evaluados por el motor real del Node. Se generaron con textos armados desde el léxico y el catálogo, más 15 bordes (vacío, blancos, emojis, 5000 caracteres). Cubre las dos vías de propuesta, la zona gris, el acoso, el titular nombrado y la ubicación. Una prueba exige igualdad exacta.
35. Con la Fase 6, 36 de las 37 operaciones de `v1.json` están implementadas con su mismo `operationId`; falta solo `GET /eventos` (Fase 8).
36. El archivador y el clasificador son procesos de fondo sin HTTP. El archivador es un contexto propio (`archivador`) que llama a las dos funciones de la base. El clasificador vive dentro de `filtro_corrupcion` porque usa su motor y el contrato de independencia impide importarlo desde otro contexto. Los fragmentos de normas pasaron a `shared/normas.py` por la misma razón.
37. El clasificador necesita el filtro de queja y reclamo, que el plan no listaba: se migró en esta fase. Su léxico (132 frases) y el mapa de señales a normas (14 temas) son datos generados desde el Node.
38. Sin Ollama, el clasificador migrado es el algorítmico `coincidencias-v1`: reglas de corrupción, señales de queja y reclamo y apoyo de los antecedentes humanos por semejanza (`pg_trgm`). La versión guardada es `<versión de reglas>+coincidencias-v1`; `modelo` y `decision.pesoIa` quedan nulos, como en el Node sin modelo.
39. El dominio es síncrono por una guardiana: la clasificación se parte en `clasificar_por_reglas` y `aplicar_coincidencias`, y la aplicación espera al buscador de antecedentes. El buscador solo se consulta si las reglas no piden revisión de OTRANS.
40. `CicloPeriodico` ejecuta el ciclo de inmediato y luego cada intervalo; `detener` espera al ciclo en curso, como el `detener()` del Node. `ProcesosDeFondo` agrupa los ciclos y arranca y se detiene con el `lifespan`, antes de cerrar el motor.
41. `CLASIFICADOR_MODO=externo` (el valor por defecto) no arranca el clasificador dentro del servidor. `python -m app clasificador` lo corre como proceso aparte y `--una-vez` hace una sola pasada; sale con código 1 si se detiene por un error.
42. El archivador toma `pg_try_advisory_xact_lock` en cada transacción: si otra instancia lo tiene, la pasada devuelve 0. Es un cinturón sobre el worker único que el Node no tiene.
43. Corpus de oro del clasificador: `tests/fixtures/corpus_clasificacion_node.json` guarda 640 casos (de 905 generados) con categoría, confianza, motivo, versión y señales guardadas del motor real del Node. Los enteros se escriben sin decimales, como `JSON.stringify`, y una prueba lo comprueba. Además se comparó una vez con el Node sobre dos bases gemelas: 144 casos clasificados por cada lado, 48 con apoyo de antecedentes, sin ninguna diferencia.
44. Diferencias menores con el Node: el resumen del ciclo no lleva `degradadas` (sin modelo siempre es cero) y los registros conservan el texto del Node con los campos en `snake_case`.

## Fases

| Fase | Alcance | Estado |
|---|---|---|
| 0 | Preparación: contrato de referencia, base plantilla, sustitución del ejemplo por el contexto `catalogos` con `GET /v1/catalogos/plazos` | Hecha (PR #1) |
| 1 | Contrato de errores del Node (`success`, 400 de validación, 404 por método, los 18 códigos) | Hecha (PR #2) |
| 2 | Infraestructura transversal: actor y transacción, cookie firmada, sesión, CSRF, limitador, cabeceras | Hecha (PR #3) |
| 3 | `acceso` y `usuarios`, y `GET /areas` | Hecha (PR #4) |
| 4 | `incidencias`, lectura y evidencias | Hecha (PR #5) |
| 5 | `incidencias`, las siete acciones | Hecha (PR #6) |
| 6 | `derivaciones`, `consulta_ipress`, `indicadores`, `analisis` y `filtro_corrupcion` | Hecha (PR #7) |
| 7 | Archivador y clasificador | Hecha en su rama |
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
