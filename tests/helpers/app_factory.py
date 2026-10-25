from dataclasses import replace

from httpx import ASGITransport, AsyncClient

from app.acceso.application.cerrar_sesion import CerrarSesion
from app.acceso.application.iniciar_sesion import IniciarSesion
from app.catalogos.application.listar_areas import ListarAreas
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container, create_app
from app.incidencias.application.consulta_de_ipress import (
    ConsultarIncidenciaDeIpress,
    ContarIncidenciasDeIpress,
    ContenidoDeEvidenciaDeIpress,
    ListarIncidenciasDeIpress,
    ObtenerIndicadoresDeIpress,
    ObtenerResumenDeIpress,
)
from app.incidencias.application.consultar_analisis import ConsultarAnalisis
from app.incidencias.application.consultar_derivacion import ConsultarDerivacion
from app.incidencias.application.consultar_incidencia import ConsultarIncidencia
from app.incidencias.application.contar_derivaciones import ContarDerivaciones
from app.incidencias.application.contar_incidencias import ContarIncidencias
from app.incidencias.application.contenido_de_evidencia import ContenidoDeEvidencia
from app.incidencias.application.contenido_de_evidencia_derivada import ContenidoDeEvidenciaDerivada
from app.incidencias.application.ejecutar_accion import EjecutarAccion
from app.incidencias.application.incidencias_por_vencer import IncidenciasPorVencer
from app.incidencias.application.listar_derivaciones import ListarDerivaciones
from app.incidencias.application.listar_incidencias import ListarIncidencias
from app.incidencias.application.listar_ipress import ListarIpress
from app.incidencias.application.obtener_indicadores import ObtenerIndicadores
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
from tests.helpers.analisis_en_memoria import AnalisisEnMemoria
from tests.helpers.builders import los_plazos_del_catalogo, una_seguridad, una_sesion
from tests.helpers.derivaciones_en_memoria import DerivacionesEnMemoria
from tests.helpers.fakes import (
    FixedClock,
    InMemoryPlazoRepository,
    RaisingPlazoRepository,
    SesionesEnMemoria,
    StaticDatabaseProbe,
)
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria
from tests.helpers.indicadores_en_memoria import IndicadoresEnMemoria, IpressEnMemoria
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
    derivaciones: DerivacionesEnMemoria | None = None,
    indicadores: IndicadoresEnMemoria | None = None,
    ipress: IpressEnMemoria | None = None,
    analisis: AnalisisEnMemoria | None = None,
) -> Container:
    plazos = repositorio or InMemoryPlazoRepository(los_plazos_del_catalogo())
    almacen = usuarios or UsuariosEnMemoria()
    sesiones = sesiones_de_acceso or SesionesDeAccesoEnMemoria()
    claves = hasher or HasherFalso()
    casos = incidencias or IncidenciasEnMemoria()
    envios = derivaciones or DerivacionesEnMemoria()
    plazos_de_incidencia = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
    consultar_incidencia = ConsultarIncidencia(casos, plazos_de_incidencia)
    contenido_de_evidencia = ContenidoDeEvidencia(casos)
    listar_incidencias = ListarIncidencias(casos, plazos_de_incidencia)
    contar_incidencias = ContarIncidencias(casos, plazos_de_incidencia)
    lector_de_indicadores = indicadores or IndicadoresEnMemoria()
    buscador_de_ipress = ipress or IpressEnMemoria()
    obtener_indicadores = ObtenerIndicadores(lector_de_indicadores, plazos_de_incidencia)
    return Container(
        listar_plazos=ListarPlazos(plazos),
        listar_areas=ListarAreas(areas or AreasEnMemoria()),
        iniciar_sesion=IniciarSesion(usuarios_de_acceso or UsuariosDeAccesoEnMemoria(), sesiones, claves, 8),
        cerrar_sesion=CerrarSesion(sesiones),
        listar_usuarios=ListarUsuarios(almacen),
        crear_usuario=CrearUsuario(almacen, claves),
        actualizar_usuario=ActualizarUsuario(almacen),
        restablecer_clave=RestablecerClave(almacen, claves),
        listar_incidencias=listar_incidencias,
        contar_incidencias=contar_incidencias,
        incidencias_por_vencer=IncidenciasPorVencer(casos, plazos_de_incidencia),
        consultar_incidencia=consultar_incidencia,
        contenido_de_evidencia=contenido_de_evidencia,
        ejecutar_accion=EjecutarAccion(casos, casos, plazos_de_incidencia),
        listar_derivaciones=ListarDerivaciones(envios),
        contar_derivaciones=ContarDerivaciones(envios),
        consultar_derivacion=ConsultarDerivacion(envios, consultar_incidencia),
        contenido_de_evidencia_derivada=ContenidoDeEvidenciaDerivada(contenido_de_evidencia),
        consultar_analisis=ConsultarAnalisis(casos, analisis or AnalisisEnMemoria()),
        obtener_indicadores=obtener_indicadores,
        listar_ipress=ListarIpress(buscador_de_ipress),
        resumen_de_ipress=ObtenerResumenDeIpress(buscador_de_ipress, lector_de_indicadores),
        indicadores_de_ipress=ObtenerIndicadoresDeIpress(buscador_de_ipress, obtener_indicadores),
        listar_incidencias_de_ipress=ListarIncidenciasDeIpress(buscador_de_ipress, listar_incidencias),
        contar_incidencias_de_ipress=ContarIncidenciasDeIpress(buscador_de_ipress, contar_incidencias),
        consultar_incidencia_de_ipress=ConsultarIncidenciaDeIpress(buscador_de_ipress, consultar_incidencia),
        contenido_de_evidencia_de_ipress=ContenidoDeEvidenciaDeIpress(buscador_de_ipress, contenido_de_evidencia),
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
