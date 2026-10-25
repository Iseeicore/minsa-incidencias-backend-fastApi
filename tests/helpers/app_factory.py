from httpx import ASGITransport, AsyncClient

from app.composition import Container, create_app
from app.nota.application.consultar_nota import ConsultarNota
from app.nota.application.crear_nota import CrearNota
from app.shared.ports import DatabaseProbe
from tests.helpers.fakes import (
    FixedClock,
    InMemoryNotaRepository,
    RaisingNotaRepository,
    SequentialCodeGenerator,
    StaticDatabaseProbe,
)


def un_contenedor(
    repositorio: InMemoryNotaRepository | RaisingNotaRepository | None = None,
    base_disponible: bool = True,  # noqa: FBT001, FBT002
    sonda: DatabaseProbe | None = None,
) -> Container:
    notas = repositorio or InMemoryNotaRepository()
    clock = FixedClock()
    return Container(
        crear_nota=CrearNota(notas, SequentialCodeGenerator(), clock),
        consultar_nota=ConsultarNota(notas),
        database_probe=sonda or StaticDatabaseProbe(base_disponible),
        clock=clock,
    )


def un_cliente(
    contenedor: Container,
    docs_enabled: bool = False,  # noqa: FBT001, FBT002
    cors_origins: tuple[str, ...] = (),
) -> AsyncClient:
    app = create_app(contenedor, docs_enabled=docs_enabled, cors_origins=cors_origins)
    return AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://prueba")
