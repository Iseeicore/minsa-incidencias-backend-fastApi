import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

PLANTILLA_POR_DEFECTO = "bd_plantilla_desechable"
SUFIJOS_DESECHABLES = ("_desechable", "_dev", "_local")
CARPETAS_SQL = ("sql/functions", "sql/triggers")
ARCHIVO_COMENTARIOS = "sql/comentarios.sql"
CARPETA_SEMILLAS = "seeds/catalogos"
ESPERA_DE_BLOQUEO = "5s"
DURACION_MAXIMA = "120s"
CLAVE_DE_CANDADO = 7421001
CODIGO_DE_ERROR_DE_USO = 2


def archivos_sql(raiz: Path, carpeta: str) -> list[Path]:
    return sorted((raiz / carpeta).glob("*.sql"), key=lambda archivo: archivo.name)


def migraciones(raiz: Path) -> list[Path]:
    return [carpeta / "migration.sql" for carpeta in sorted((raiz / "migrations").iterdir()) if carpeta.is_dir()]


def script_de_funciones_y_semillas(raiz: Path) -> str:
    archivos = [
        *(archivo for carpeta in CARPETAS_SQL for archivo in archivos_sql(raiz, carpeta)),
        raiz / ARCHIVO_COMENTARIOS,
        *archivos_sql(raiz, CARPETA_SEMILLAS),
    ]
    cuerpo = [archivo.read_text(encoding="utf-8").strip() for archivo in archivos]
    cabecera = [
        "BEGIN;",
        f"SET LOCAL lock_timeout = '{ESPERA_DE_BLOQUEO}';",
        f"SET LOCAL statement_timeout = '{DURACION_MAXIMA}';",
        f"SELECT pg_advisory_xact_lock({CLAVE_DE_CANDADO});",
    ]
    return "\n\n".join([*cabecera, *cuerpo, "COMMIT;"]) + "\n"


def recrear_base(url: str, plantilla: str) -> None:
    with psycopg.connect(url, autocommit=True) as administrador:
        administrador.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(plantilla)))
        administrador.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(plantilla)))


def aplicar(url: str, plantilla: str, raiz: Path) -> None:
    with psycopg.connect(make_conninfo(url, dbname=plantilla), autocommit=True) as conexion:
        for migracion in migraciones(raiz):
            conexion.execute(migracion.read_text(encoding="utf-8"))
        conexion.execute(script_de_funciones_y_semillas(raiz))


def main() -> int:
    raiz = Path(os.environ.get("BOT_PRISMA_DIR", ""))
    url = os.environ.get("TEST_DATABASE_URL", "")
    plantilla = os.environ.get("TEST_TEMPLATE_DATABASE", PLANTILLA_POR_DEFECTO)
    if not (raiz / "migrations").is_dir() or not url:
        sys.stderr.write("Define BOT_PRISMA_DIR (carpeta prisma del bot) y TEST_DATABASE_URL.\n")
        return CODIGO_DE_ERROR_DE_USO
    if not plantilla.endswith(SUFIJOS_DESECHABLES):
        sys.stderr.write(f"La plantilla debe terminar en {', '.join(SUFIJOS_DESECHABLES)}.\n")
        return CODIGO_DE_ERROR_DE_USO
    recrear_base(url, plantilla)
    aplicar(url, plantilla, raiz)
    sys.stdout.write(f"Plantilla {plantilla} lista.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
