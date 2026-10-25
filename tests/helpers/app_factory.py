from dataclasses import replace

from httpx import ASGITransport, AsyncClient

from app.acceso.application.cerrar_sesion import CerrarSesion
from app.acceso.application.iniciar_sesion import IniciarSesion
from app.catalogos.application.listar_areas import ListarAreas
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
from app.incidencias.application.contar_incidencias import ContarIncidencias
from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
from app.incidencias.application.incidencias_por_vencer import IncidenciasPorVencer
from app.incidencias.application.listar_incidencias import ListarIncidencias
from app.incidencias.domain.plazo import PlazosConfigurados
from app.shared.http_security import HttpSecurity
from app.shared.ports import DatabaseProbe, SessionResolver
from app.shared.sesion import SesionActual
from app.shared.token_bucket import TokenBucketLimiter
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.application.crear_usuario import CrearUsuario
from app.usuarios.application.listar_usuarios import ListarUsuarios
from app.usuarios.application.restablecer_clave import RestablecerClave
from tests.helpers.acceso_en_memoria import (
    AreasEnMemoria,
    HasherFalso,
    SesionesDeAccesoEnMemoria,
    UsuariosDeAccesoEnMemoria,
)
from tests.helpers.builders import los_plazos_del_catalogo, una_seguridad, una_sesion
from tests.helpers.fakes import (
    FixedClock,
    InMemoryPlazoRepository,
    RaisingPlazoRepository,
    SesionesEnMemoria,
    StaticDatabaseProbe,
)
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria
from tests.helpers.sesion import SesionDePrueba
from tests.helpers.usuarios_en_memoria import UsuariosEnMemoria


def un_contenedor(  # noqa: PLR0913, PLR0917
    repositorio: InMemoryPlazoRepository | RaisingPlazoRepository | None = None,
    base_disponible: bool = True,  # noqa: FBT001, FBT002
    sonda: DatabaseProbe | None = None,
    resolvedor: SessionResolver | None = None,
    seguridad: HttpSecurity | None = None,
    limitador: TokenBucketLimiter | None = None,
    usuarios: UsuariosEnMemoria | None = None,
    usuarios_de_acceso: UsuariosDeAccesoEnMemoria | None = None,
    sesiones_de_acceso: SesionesDeAccesoEnMemoria | None = None,
    areas: AreasEnMemoria | None = None,
    hasher: HasherFalso | None = None,
    incidencias: IncidenciasEnMemoria | None = None,
) -> Container:
    plazos = repositorio or InMemoryPlazoRepository(los_plazos_del_catalogo())
    almacen = usuarios or UsuariosEnMemoria()
    sesiones = sesiones_de_acceso or SesionesDeAccesoEnMemoria()
    claves = hasher or HasherFalso()
    casos = incidencias or IncidenciasEnMemoria()
    plazos_de_incidencia = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
    return Container(
        listar_plazos=ListarPlazos(plazos),
        listar_areas=ListarAreas(areas or AreasEnMemoria()),
        iniciar_sesion=IniciarSesion(usuarios_de_acceso or UsuariosDeAccesoEnMemoria(), sesiones, claves, 8),
        cerrar_sesion=CerrarSesion(sesiones),
        listar_usuarios=ListarUsuarios(almacen),
        crear_usuario=CrearUsuario(almacen, claves),
        actualizar_usuario=ActualizarUsuario(almacen),
        restablecer_clave=RestablecerClave(almacen, claves),
        listar_incidencias=ListarIncidencias(casos, plazos_de_incidencia),
        contar_incidencias=ContarIncidencias(casos, plazos_de_incidencia),
        incidencias_por_vencer=IncidenciasPorVencer(casos, plazos_de_incidencia),
        consultar_incidencia=ConsultarIncidencia(casos, plazos_de_incidencia),
        contenido_de_evidencia=ContenidoDeEvidencia(casos),
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
    sesion: SesionActual | None = None,
) -> AsyncClient:
    if cors_origins:
        contenedor = replace(contenedor, security=replace(contenedor.security, allowed_origins=cors_origins))
    app = create_app(contenedor, docs_enabled=docs_enabled)
    destino = SesionDePrueba(app, sesion or una_sesion()) if con_sesion else app
    return AsyncClient(transport=ASGITransport(app=destino, raise_app_exceptions=False), base_url="http://prueba")
