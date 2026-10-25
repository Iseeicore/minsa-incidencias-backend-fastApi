# Contrato de referencia del backend Node

`v1.json` y `salud.json` son copias idénticas, byte a byte, de `docs/openapi/` del repositorio `minsa-incidencias-backend`.

| Dato | Valor |
|---|---|
| Repositorio de origen | `Iseeicore/minsa-incidencias-backend` |
| Rama y commit de origen | `main` en `6e3205a` (merge del PR #15) |
| OpenAPI | 3.1.0, `info.version` 1.0.0, `servers: /v1` |
| Alcance | 36 rutas, 37 operaciones y 19 esquemas |
| Huella de `v1.json` (`git hash-object`) | `4314c070efc96670602be2d36795a259f08de83d` |
| Huella de `salud.json` (`git hash-object`) | `a4b8d110f83c762da96c0ad249420e09f2f2d4c1` |

Estos archivos son la especificación contra la que se mide la paridad (`tests/paridad/`). Cuando el Node cambie su contrato, se vuelven a copiar y se actualiza esta tabla en el mismo cambio. No se editan a mano.
