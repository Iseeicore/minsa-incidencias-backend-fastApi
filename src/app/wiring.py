from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import make_url

from app.acceso.adapters.persistence.sesiones import SqlSesionStore
from app.acceso.adapters.persistence.usuarios import SqlUsuarioFinder
from app.acceso.application.cerrar_sesion import CerrarSesion
from app.acceso.application.iniciar_sesion import IniciarSesion
from app.acceso.application.resolver_sesion import ResolverSesion
from app.archivador.adapters.persistence.archivado import SqlArchivadoRepositorio
from app.archivador.application.archivar_incidencias import ArchivarIncidencias
from app.catalogos.adapters.persistence.areas import SqlAreaFinder
from app.catalogos.adapters.persistence.repository import SqlPlazoRepository
from app.catalogos.application.listar_areas import ListarAreas
from app.catalogos.application.listar_plazos import ListarPlazos
from app.composition import Container
from app.constants.clasificacion import INTERVALO_SONDEO_SEGUNDOS
from app.constants.limits import MS_PER_SECOND
from app.constants.sesion import SECONDS_PER_HOUR
from app.enums.clasificador_modo import ClasificadorModo
from app.enums.node_env import NodeEnv
from app.eventos.adapters.persistence.categorias import SqlCategoriasPorRol
from app.eventos.adapters.persistence.notificaciones import AbridorDeConexionPostgres, SqlInstaladorDeNotificaciones
from app.eventos.adapters.tiempo import TiempoAsyncio
from app.eventos.application.escuchar_cambios import EscucharCambios
from app.eventos.application.publicar_cambios import PublicarCambios
from app.eventos.application.suscribirse_a_eventos import SuscribirseAEventos
from app.eventos.domain.centro_de_eventos import CentroDeEventos
from app.filtro_corrupcion.adapters.persistence.clasificador import SqlAlarmaReader, SqlClasificadorUnitOfWork
from app.filtro_corrupcion.application.clasificar_incidencias import ClasificadorIncidencias
from app.filtro_corrupcion.application.evaluar_corrupcion import EvaluarCorrupcion
from app.filtro_corrupcion.application.trabajador_clasificador import TrabajadorClasificador
from app.incidencias.adapters.persistence.analisis import SqlAnalisisReader
from app.incidencias.adapters.persistence.derivaciones import SqlDerivacionReader
from app.incidencias.adapters.persistence.escritura import SqlIncidenciaUnitOfWork
from app.incidencias.adapters.persistence.indicadores import SqlIndicadoresReader
from app.incidencias.adapters.persistence.ipress import SqlIpressFinder
from app.incidencias.adapters.persistence.repository import SqlIncidenciaReader
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
from app.shared.ciclo_periodico import CicloPeriodico, ProcesosDeFondo
from app.shared.clock import SystemClock
from app.shared.database import SqlDatabaseProbe
from app.shared.http_security import HttpSecurity
from app.shared.password_hasher import Argon2PasswordHasher
from app.shared.rate_limit import RateLimitPolicies
from app.shared.session_cookie import SessionCookieConfig
from app.shared.token_bucket import BucketPolicy
from app.usuarios.adapters.persistence.repository import SqlUsuarioReader, SqlUsuarioUnitOfWork
from app.usuarios.application.actualizar_usuario import ActualizarUsuario
from app.usuarios.application.crear_administrador import CrearAdministrador
from app.usuarios.application.crear_usuario import CrearUsuario
from app.usuarios.application.crear_usuario_de_prueba import CrearUsuarioDePrueba
from app.usuarios.application.listar_usuarios import ListarUsuarios
from app.usuarios.application.restablecer_clave import RestablecerClave

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.config.settings import Settings
    from app.shared.ports import RegistroDeProcesos
    from app.shared.token_bucket import TokenBucketLimiter


def build_security(settings: Settings) -> HttpSecurity:
    window = settings.rate_limit_login_window_seconds
    return HttpSecurity(
        cookies=SessionCookieConfig(
            secrets=(
                settings.cookie_secret.get_secret_value(),
                *(secret.get_secret_value() for secret in settings.cookie_secret_previous),
            ),
            production=settings.node_env == NodeEnv.PRODUCTION,
        ),
        rate_limits=RateLimitPolicies(
            authenticated=BucketPolicy(settings.rate_limit_auth_capacity, settings.rate_limit_window_seconds),
            anonymous=BucketPolicy(settings.rate_limit_anon_capacity, settings.rate_limit_window_seconds),
        ),
        login_by_email=BucketPolicy(settings.rate_limit_login_capacity, window),
        login_by_ip=BucketPolicy(settings.rate_limit_login_ip_capacity, window),
        session_max_age_seconds=settings.session_absolute_hours * SECONDS_PER_HOUR,
        allowed_origins=tuple(settings.cors_origins),
        trust_proxy=settings.trust_proxy,
    )


@dataclass(frozen=True, slots=True)
class Eventos:
    centro: CentroDeEventos
    escuchar: EscucharCambios


def build_eventos(settings: Settings, engine: AsyncEngine, registro: RegistroDeProcesos) -> Eventos:
    tiempo = TiempoAsyncio()
    centro = CentroDeEventos(tiempo, registro)
    publicar = PublicarCambios(centro, SqlCategoriasPorRol(engine), tiempo, registro)
    url = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql")
    abridor = AbridorDeConexionPostgres(
        url.render_as_string(hide_password=False), max(1, settings.db_connection_timeout_ms // MS_PER_SECOND)
    )
    return Eventos(centro, EscucharCambios(SqlInstaladorDeNotificaciones(engine), abridor, publicar, registro))


def build_crear_administrador(engine: AsyncEngine) -> CrearAdministrador:
    return CrearAdministrador(SqlUsuarioUnitOfWork(engine), Argon2PasswordHasher())


def build_crear_usuario_de_prueba(engine: AsyncEngine) -> CrearUsuarioDePrueba:
    return CrearUsuarioDePrueba(SqlUsuarioUnitOfWork(engine), Argon2PasswordHasher())


def build_trabajador_clasificador(engine: AsyncEngine, registro: RegistroDeProcesos) -> TrabajadorClasificador:
    clasificador = ClasificadorIncidencias(SqlClasificadorUnitOfWork(engine))
    return TrabajadorClasificador(clasificador, SqlAlarmaReader(engine), registro)


def build_procesos(settings: Settings, engine: AsyncEngine, registro: RegistroDeProcesos) -> ProcesosDeFondo:
    archivador = ArchivarIncidencias(
        SqlArchivadoRepositorio(engine),
        registro,
        vigencia_dias=settings.vigencia_resolucion_dias,
        lote=settings.archivado_lote,
    )
    ciclos = [CicloPeriodico(archivador.ejecutar_con_registro, settings.archivado_interval_seconds)]
    if settings.clasificador_modo == ClasificadorModo.SONDEO:
        trabajador = build_trabajador_clasificador(engine, registro)
        ciclos.append(CicloPeriodico(trabajador.ejecutar_ciclo, INTERVALO_SONDEO_SEGUNDOS))
    return ProcesosDeFondo(ciclos)


def build_container(
    settings: Settings, engine: AsyncEngine, limiter: TokenBucketLimiter, centro: CentroDeEventos | None = None
) -> Container:
    hasher = Argon2PasswordHasher()
    sesiones = SqlSesionStore(engine)
    seguimiento = centro if centro is not None else CentroDeEventos(TiempoAsyncio(), structlog.get_logger())
    usuarios_uow = SqlUsuarioUnitOfWork(engine)
    incidencias = SqlIncidenciaReader(engine)
    derivaciones = SqlDerivacionReader(engine)
    plazos = PlazosConfigurados(settings.vigencia_resolucion_dias, settings.plazo_aviso_horas)
    ipress = SqlIpressFinder(engine)
    consultar_incidencia = ConsultarIncidencia(incidencias, plazos)
    contenido_de_evidencia = ContenidoDeEvidencia(incidencias)
    listar_incidencias = ListarIncidencias(incidencias, plazos)
    contar_incidencias = ContarIncidencias(incidencias, plazos)
    indicadores = SqlIndicadoresReader(engine)
    obtener_indicadores = ObtenerIndicadores(indicadores, plazos)
    return Container(
        listar_plazos=ListarPlazos(SqlPlazoRepository(engine)),
        listar_areas=ListarAreas(SqlAreaFinder(engine)),
        iniciar_sesion=IniciarSesion(SqlUsuarioFinder(engine), sesiones, hasher, settings.session_absolute_hours),
        cerrar_sesion=CerrarSesion(sesiones, seguimiento),
        listar_usuarios=ListarUsuarios(SqlUsuarioReader(engine)),
        crear_usuario=CrearUsuario(usuarios_uow, hasher),
        actualizar_usuario=ActualizarUsuario(usuarios_uow, seguimiento),
        restablecer_clave=RestablecerClave(usuarios_uow, hasher, seguimiento),
        listar_incidencias=listar_incidencias,
        contar_incidencias=contar_incidencias,
        incidencias_por_vencer=IncidenciasPorVencer(incidencias, plazos),
        consultar_incidencia=consultar_incidencia,
        contenido_de_evidencia=contenido_de_evidencia,
        ejecutar_accion=EjecutarAccion(SqlIncidenciaUnitOfWork(engine), incidencias, plazos),
        listar_derivaciones=ListarDerivaciones(derivaciones),
        contar_derivaciones=ContarDerivaciones(derivaciones),
        consultar_derivacion=ConsultarDerivacion(derivaciones, consultar_incidencia),
        contenido_de_evidencia_derivada=ContenidoDeEvidenciaDerivada(contenido_de_evidencia),
        consultar_analisis=ConsultarAnalisis(incidencias, SqlAnalisisReader(engine)),
        evaluar_corrupcion=EvaluarCorrupcion(),
        suscribirse_a_eventos=SuscribirseAEventos(seguimiento),
        obtener_indicadores=obtener_indicadores,
        listar_ipress=ListarIpress(ipress),
        resumen_de_ipress=ObtenerResumenDeIpress(ipress, indicadores),
        indicadores_de_ipress=ObtenerIndicadoresDeIpress(ipress, obtener_indicadores),
        listar_incidencias_de_ipress=ListarIncidenciasDeIpress(ipress, listar_incidencias),
        contar_incidencias_de_ipress=ContarIncidenciasDeIpress(ipress, contar_incidencias),
        consultar_incidencia_de_ipress=ConsultarIncidenciaDeIpress(ipress, consultar_incidencia),
        contenido_de_evidencia_de_ipress=ContenidoDeEvidenciaDeIpress(ipress, contenido_de_evidencia),
        database_probe=SqlDatabaseProbe(engine, timeout_seconds=settings.db_connection_timeout_ms / MS_PER_SECOND),
        clock=SystemClock(),
        session_resolver=ResolverSesion(sesiones, settings.session_idle_minutes, seguimiento),
        limiter=limiter,
        security=build_security(settings),
    )
