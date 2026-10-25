# Despliegue

Lo que Infraestructura necesita para correr este servicio. Todo está verificado contra el código; las variables y sus valores por defecto están en el README.

## Qué corre

Una imagen (`Dockerfile`) y un proceso por contenedor: `python -m app`. Escucha en `PORT` (3033 por defecto) y corre dentro del mismo proceso:

- El API (`/v1/...`) y el flujo de eventos en vivo (`GET /v1/eventos`).
- El archivador de incidencias, al arrancar y luego cada `ARCHIVADO_INTERVAL_SECONDS`.
- Opcionalmente el clasificador, si `CLASIFICADOR_MODO=sondeo`.

Con `CLASIFICADOR_MODO=externo` (el valor por defecto) el servidor no clasifica. En ese caso hay que correr aparte, con la misma imagen y el mismo entorno, **un solo** proceso: `python -m app clasificador`.

Un solo proceso por contenedor y, mientras no se pida otra cosa, **una sola réplica**: el limitador de peticiones, el conteo de flujos abiertos (3 por usuario, 500 en total) y la cola de eventos son por proceso. Con más réplicas los límites se multiplican. El archivador toma un candado en la base, así que dos réplicas no archivan a la vez; el clasificador toma los casos con bloqueo de fila, así que dos clasificadores tampoco se pisan.

## Variables de entorno

Son las mismas del backend Node, con los mismos nombres y valores por defecto. Solo cambia lo que sigue:

| Variable | Obligatoria | Qué hacer |
|---|---|---|
| `DATABASE_URL` | Sí | La define Infraestructura. Una conexión directa a PostgreSQL 16, no un pool en modo transacción (ver «Base de datos»). |
| `COOKIE_SECRET` | Sí | 32 caracteres como mínimo. Para rotarlo, poner el anterior en `COOKIE_SECRET_PREVIOUS` mientras dure la vigencia de las sesiones. |
| `NODE_ENV` | No, pero conviene definirla | Aquí vale `production` si no se define (en el Node valía `development`). En producción la cookie se llama `__Host-gestion_sid`, es `Secure` y exige HTTPS; fuera de producción se sirven `/docs`, `/redoc` y `/openapi.json`. |
| `CORS_ORIGINS` | No | Los orígenes del frontend, separados por coma, con esquema y puerto, sin ruta. Vacío bloquea a los navegadores. |
| `TRUST_PROXY` | No | `true` detrás de un balanceador. Además hay que definir `FORWARDED_ALLOW_IPS` con las IP del proxy (uvicorn solo confía en esas; no usar `*`). |
| `CLASIFICADOR_MODO` | No | `externo` o `sondeo`; ver arriba. |
| `DB_IDLE_TIMEOUT_MS` | No | Aquí se usa para reciclar conexiones por antigüedad; es una aproximación de la inactividad del pool de Node. |

Variables solo para los comandos de una sola vez (no van en el servicio):

| Comando | Variables |
|---|---|
| `python -m app crear-admin` | `ADMIN_NOMBRE`, `ADMIN_CORREO`, `ADMIN_PASSWORD` (12 caracteres como mínimo), `ADMIN_AREA` (opcional, código de un área activa) |
| `python -m app crear-usuario-prueba` | `USUARIO_NOMBRE`, `USUARIO_CORREO`, `USUARIO_PASSWORD` (12 como mínimo), `USUARIO_ROL`, `USUARIO_AREA` (opcional). Se niega a correr si el nombre de la base no termina en `_desechable`, `_dev` o `_local`. |

Ninguna variable se escribe en el código ni en el repositorio. El primer administrador se crea con `crear-admin`; los demás usuarios los crea un administrador desde la API, que entrega una clave inicial.

## Base de datos

- PostgreSQL 16 con el esquema del bot de citas (`prisma/migrations` y `prisma/sql` de `minsa-citas-whatsapp-bot`). Este servicio **no migra**.
- **Disparador de avisos.** Al arrancar, el servicio instala la función `chatbot.fn_notificar_cambio_incidencia` y el disparador `trg_incidencia_paciente_notificar_cambio` si no están (o si son de otra versión), bajo un candado de la base. Es idempotente y lo hace también el Node. Si no están y el rol no puede crearlos, **el servicio no arranca**. Si ya están instalados con la versión vigente (por ejemplo, tras un primer arranque con un rol que pueda crearlos), el rol de trabajo no necesita ese privilegio.
- **Escucha.** El flujo de eventos usa `LISTEN` sobre una conexión propia, así que `DATABASE_URL` no puede pasar por un pool en modo transacción. Cada proceso usa `DB_POOL_MAX` conexiones más una de escucha; el clasificador externo usa su propio pool.
- **Funciones y extensiones.** El archivado usa `chatbot.archivar_incidencias_vencidas` y `chatbot.archivar_incidencias_resueltas`. La búsqueda de usuarios usa `public.f_unaccent`. El clasificador usa `public.similarity` (`pg_trgm`) y `ia.entrenamiento_categoria` para apoyarse en casos ya revisados; si faltan, clasifica solo con reglas, sin fallar.

## Salud y cierre

- `GET /salud`: el proceso está vivo, no toca la base. Es el `HEALTHCHECK` de la imagen.
- `GET /salud/listo`: consulta la base y responde 503 si no puede atender. Para el balanceador.
- Los registros salen en JSON por la salida estándar, con el nivel de `LOG_LEVEL`. Los identificadores de usuario de los eventos salen enmascarados y ningún registro lleva secretos.
- Al recibir `SIGTERM` el servidor cierra primero los flujos de eventos y espera hasta 10 s a las conexiones restantes. Conviene un plazo de apagado del orquestador de al menos 15 s.

## Qué cambió respecto al Node

Nada que el frontend note: el contrato de la API es el mismo (`docs/calidad/paridad.md`). Para operar:

- El comando de arranque es `python -m app` en lugar de `node dist/server.js`; los scripts `crear-admin`, `crear-usuario-prueba` y `clasificador` son subcomandos del mismo programa.
- `NODE_ENV` tiene otro valor por defecto (ver arriba).
- `generar-openapi` no existe: el contrato de referencia es `docs/contrato/v1.json` y la especificación viva se sirve en `/v1/openapi.json` fuera de producción.
