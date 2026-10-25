from httpx import ASGITransport, AsyncClient

from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.shared.ports import DatabaseProbe
from tests.helpers.builders import los_plazos_del_catalogo, una_sesion
from tests.helpers.fakes import FixedClock, InMemoryPlazoRepository, RaisingPlazoRepository, StaticDatabaseProbe
from tests.helpers.sesion import SesionDePrueba


def un_contenedor(
    repositorio: InMemoryPlazoRepository | RaisingPlazoRepository | None = None,
    base_disponible: bool = True,  # noqa: FBT001, FBT002
    sonda: DatabaseProbe | None = None,
) -> Container:
    plazos = repositorio or InMemoryPlazoRepository(los_plazos_del_catalogo())
    return Container(
        listar_plazos=ListarPlazos(plazos),
        database_probe=sonda or StaticDatabaseProbe(base_disponible),
        clock=FixedClock(),
    )


def un_cliente(
    contenedor: Container,
    docs_enabled: bool = False,  # noqa: FBT001, FBT002
    cors_origins: tuple[str, ...] = (),
    *,
    con_sesion: bool = True,
) -> AsyncClient:
    app = create_app(contenedor, docs_enabled=docs_enabled, cors_origins=cors_origins)
    destino = SesionDePrueba(app, una_sesion()) if con_sesion else app
    return AsyncClient(transport=ASGITransport(app=destino, raise_app_exceptions=False), base_url="http://prueba")
