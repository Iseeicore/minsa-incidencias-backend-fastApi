from dataclasses import replace

from httpx import ASGITransport, AsyncClient

from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.shared.http_security import HttpSecurity
from app.shared.ports import DatabaseProbe, SessionResolver
from app.shared.token_bucket import TokenBucketLimiter
from tests.helpers.builders import los_plazos_del_catalogo, una_seguridad, una_sesion
from tests.helpers.fakes import (
    FixedClock,
    InMemoryPlazoRepository,
    RaisingPlazoRepository,
    SesionesEnMemoria,
    StaticDatabaseProbe,
)
from tests.helpers.sesion import SesionDePrueba


def un_contenedor(  # noqa: PLR0913, PLR0917
    repositorio: InMemoryPlazoRepository | RaisingPlazoRepository | None = None,
    base_disponible: bool = True,  # noqa: FBT001, FBT002
    sonda: DatabaseProbe | None = None,
    resolvedor: SessionResolver | None = None,
    seguridad: HttpSecurity | None = None,
    limitador: TokenBucketLimiter | None = None,
) -> Container:
    plazos = repositorio or InMemoryPlazoRepository(los_plazos_del_catalogo())
    return Container(
        listar_plazos=ListarPlazos(plazos),
        database_probe=sonda or StaticDatabaseProbe(base_disponible),
        clock=FixedClock(),
        session_resolver=resolvedor or SesionesEnMemoria(),
        limiter=limitador or TokenBucketLimiter(),
        security=seguridad or una_seguridad(),
    )


def un_cliente(
    contenedor: Container,
    docs_enabled: bool = False,  # noqa: FBT001, FBT002
    cors_origins: tuple[str, ...] = (),
    *,
    con_sesion: bool = True,
) -> AsyncClient:
    if cors_origins:
        contenedor = replace(contenedor, security=replace(contenedor.security, allowed_origins=cors_origins))
    app = create_app(contenedor, docs_enabled=docs_enabled)
    destino = SesionDePrueba(app, una_sesion()) if con_sesion else app
    return AsyncClient(transport=ASGITransport(app=destino, raise_app_exceptions=False), base_url="http://prueba")
