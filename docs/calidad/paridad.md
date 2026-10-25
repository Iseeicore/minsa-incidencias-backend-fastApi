# Paridad con el backend Node

Cómo se comprueba que este servicio responde lo mismo que `minsa-incidencias-backend`, y qué diferencias quedan. La referencia es `docs/contrato/v1.json`, generado desde el Node.

## Resultado

- **37 de 37 operaciones** de `v1.json` están implementadas, con el mismo `operationId`, los mismos códigos de respuesta y los mismos parámetros.
- Los cuerpos de petición y de éxito tienen las mismas propiedades y los mismos campos obligatorios, hasta 6 niveles de profundidad.
- Los motores con reglas propias (filtro de corrupción, clasificador) dan resultados idénticos sobre corpus generados con el código real del Node.
- El flujo de eventos en vivo entrega los mismos bytes que el del Node.

## Cómo se comprueba

| Técnica | Dónde | Qué compara |
|---|---|---|
| Estática | `tests/paridad/test_openapi.py` (150 pruebas) | La especificación de `/v1` contra `v1.json`: operaciones, identificadores, códigos, parámetros, cuerpos |
| Dinámica | `tests/paridad/test_*.py` y los routers | Cada respuesta real (éxito y errores 400, 401, 403 y 404, además del 429 de eventos) validada contra `v1.json` con `openapi-core` |
| Corpus de oro | `tests/fixtures/corpus_corrupcion_node.json` (835 casos), `corpus_clasificacion_node.json` (640 casos) | Resultado completo del motor real del Node, con igualdad exacta |
| Vectores | `tests/fixtures/vectores_node.json`, `hashes_argon2_node.json` | Firma de la cookie, cursores y huellas argon2 generados por el Node |
| Doble backend | Comparaciones de una sola vez, registradas en `docs/calidad/mediciones.md` | El Node y este servicio sobre dos bases gemelas: 144 casos clasificados sin diferencias, y el flujo de eventos byte a byte |

## Pruebas de integración del Node y su equivalente

| Del Node | Aquí |
|---|---|
| `routes/auth` | `tests/test_flujo_de_acceso.py`, `tests/paridad/test_acceso_usuarios_areas.py` |
| `routes/usuarios` | `tests/paridad/test_acceso_usuarios_areas.py`, `tests/usuarios/adapters/persistence/test_repository.py` |
| `routes/areas` | `tests/paridad/test_acceso_usuarios_areas.py`, `tests/catalogos/adapters/persistence/test_areas.py` |
| `routes/catalogos` | `tests/paridad/test_catalogos_plazos.py` |
| `routes/incidencias` | `tests/paridad/test_incidencias_lectura.py`, `tests/paridad/test_incidencias_acciones.py` |
| `routes/analisis-incidencia` | `tests/paridad/test_analisis.py`, `tests/incidencias/adapters/persistence/test_analisis.py` |
| `routes/consulta-ipress` | `tests/paridad/test_indicadores_ipress.py`, `tests/incidencias/adapters/persistence/test_ipress.py` |
| `routes/indicadores` | `tests/paridad/test_indicadores_ipress.py`, `tests/incidencias/adapters/persistence/test_indicadores.py` |
| `routes/eventos` | `tests/eventos/test_flujo_en_vivo.py` (con un servidor uvicorn real) |
| `database/pg-database` | `tests/shared/test_database_integration.py`, `tests/shared/test_transaction.py` |
| `repositories/coincidencias-clasificacion` | `tests/filtro_corrupcion/adapters/persistence/test_clasificador_coincidencias.py` |
| `services/clasificador/clasificador` | `tests/filtro_corrupcion/adapters/persistence/test_clasificador.py`, `tests/paridad/test_clasificacion.py` |
| `services/archivador-incidencias` | `tests/archivador/adapters/persistence/test_archivado.py` |
| `services/eventos/cambios-postgres` | `tests/eventos/adapters/persistence/test_notificaciones.py` |
| `services/usuario-prueba.service` | `tests/test_comandos_de_usuarios.py`, `tests/usuarios/application/test_crear_usuario_de_prueba.py` |

No se portó `services/analisis-ia/casos/casos`: pertenece al análisis con modelo de lenguaje (Ollama), que queda fuera de esta entrega.

## Diferencias conocidas

Ninguna cambia el contrato que ve el frontend.

- **Fuera de alcance:** el cliente Ollama, `analizar-mensaje`, la comparación de variantes, `casos/` de IA e `ia-poc`. El clasificador migrado es el algorítmico `coincidencias-v1`.
- **Orden de `details`** cuando una petición trae varios errores de filtro: puede salir en otro orden.
- **Ficha de derivación de un análisis guardado:** aquí se tipa y se descarta (`null`) si no tiene la forma esperada; el Node la devuelve sin validar.
- **Resumen del ciclo del clasificador:** no lleva `degradadas`, porque sin modelo siempre es cero.
- **Vencimiento de la sesión en el flujo de eventos:** no se parte en tramos para evitar el desborde del temporizador de JavaScript; `asyncio` no tiene ese límite.
- **`NODE_ENV`:** vale `production` si no se define; el Node usaba `development`.
- **`DB_IDLE_TIMEOUT_MS`:** recicla conexiones por antigüedad; es una aproximación de la inactividad del pool de Node.
