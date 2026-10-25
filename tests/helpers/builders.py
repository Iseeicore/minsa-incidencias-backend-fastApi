from datetime import UTC, datetime
from urllib.parse import quote

from app.acceso.domain.sesion_vigente import SesionVigente
from app.acceso.domain.usuario_interno import UsuarioInterno
from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.tipo_area import TipoArea
from app.shared.http_security import HttpSecurity
from app.shared.permisos import vistas_de_roles
from app.shared.rate_limit import RateLimitPolicies
from app.shared.sesion import AreaDeSesion, SesionActual, VigenciaDeSesion
from app.shared.session_cookie import SessionCookieConfig
from app.shared.signed_cookie import sign
from app.shared.token_bucket import BucketPolicy
from app.usuarios.domain.usuario_gestionado import UsuarioGestionado

SECRETO_DE_PRUEBA = "secreto-de-prueba-0123456789-abcdefghijklmnop"
SECRETO_ANTERIOR = "secreto-anterior-9876543210-zyxwvutsrqponmlk"
CAPACIDAD_HOLGADA = 1000
VENTANA_DE_PRUEBA = 60
DURACION_DE_SESION = 28800


def un_plazo(
    categoria: CategoriaIncidencia = CategoriaIncidencia.QUEJA,
    plazo_dias_habiles: int = 30,
    *,
    archiva_por_vencimiento: bool = True,
) -> PlazoDeCategoria:
    return PlazoDeCategoria(
        categoria=categoria,
        plazo_dias_habiles=plazo_dias_habiles,
        archiva_por_vencimiento=archiva_por_vencimiento,
    )


def los_plazos_del_catalogo() -> list[PlazoDeCategoria]:
    return [
        un_plazo(CategoriaIncidencia.DENUNCIA_CORRUPCION, 3, archiva_por_vencimiento=False),
        un_plazo(CategoriaIncidencia.QUEJA, 30),
        un_plazo(CategoriaIncidencia.RECLAMO, 30),
        un_plazo(CategoriaIncidencia.OTRO, 30),
    ]


def una_sesion(
    correo: str = "gestor@minsa.gob.pe", roles: tuple[str, ...] = ("GESTOR",), area: AreaDeSesion | None = None
) -> SesionActual:
    return SesionActual(
        sesion_id="6f1c2c9e-7a49-4a39-9d44-2f6e9d6a0001",
        usuario_id="0b7a5c1e-31a2-4b7e-8c0d-5f4f5c2d0001",
        correo=correo,
        nombre_completo="Gestor de Prueba",
        roles=roles,
        area=area,
        vistas=vistas_de_roles(roles),
    )


def un_area_de_sesion(id: int = 1, tipo: TipoArea = TipoArea.ESTABLECIMIENTO) -> AreaDeSesion:  # noqa: A002
    return AreaDeSesion(id=id, codigo="HOSP-01", nombre="Hospital Uno", tipo=tipo)


def un_usuario_gestionado(  # noqa: PLR0913
    id: str = "11111111-1111-4111-8111-111111111111",  # noqa: A002
    nombre_completo: str = "Ana Torres",
    correo: str = "ana@minsa.gob.pe",
    rol: str | None = "GESTOR",
    area_id: int | None = 1,
    *,
    activo: bool = True,
) -> UsuarioGestionado:
    return UsuarioGestionado(
        id=id,
        nombre_completo=nombre_completo,
        correo=correo,
        activo=activo,
        rol=rol,
        area_id=area_id,
        area_codigo="HOSP-01" if area_id == 1 else ("HOSP-02" if area_id == 2 else None),
        area_nombre="Hospital Uno" if area_id == 1 else ("Hospital Dos" if area_id == 2 else None),
    )


def un_usuario_interno(
    correo: str = "gestor@minsa.gob.pe",
    password_hash: str = "hash:clave-correcta",  # noqa: S107
    *,
    activo: bool = True,
) -> UsuarioInterno:
    return UsuarioInterno(
        id="0b7a5c1e-31a2-4b7e-8c0d-5f4f5c2d0001",
        correo=correo,
        nombre_completo="Gestor de Prueba",
        password_hash=password_hash,
        activo=activo,
    )


def una_sesion_vigente(*, debe_tocar: bool = False) -> SesionVigente:
    base = una_sesion()
    return SesionVigente(
        sesion_id=base.sesion_id,
        usuario_id=base.usuario_id,
        correo=base.correo,
        nombre_completo=base.nombre_completo,
        roles=base.roles,
        area=None,
        debe_tocar=debe_tocar,
        vigencia=una_vigencia(),
    )


def una_vigencia() -> VigenciaDeSesion:
    return VigenciaDeSesion(
        vence_en=datetime(2026, 10, 24, 20, 0, tzinfo=UTC), inactiva_en=datetime(2026, 10, 24, 12, 30, tzinfo=UTC)
    )


def una_politica(capacidad: int = CAPACIDAD_HOLGADA, ventana: int = VENTANA_DE_PRUEBA) -> BucketPolicy:
    return BucketPolicy(capacity=capacidad, window_seconds=ventana)


def una_config_de_cookie(*, produccion: bool = False) -> SessionCookieConfig:
    return SessionCookieConfig(secrets=(SECRETO_DE_PRUEBA, SECRETO_ANTERIOR), production=produccion)


def una_seguridad(
    origenes: tuple[str, ...] = (),
    politicas: RateLimitPolicies | None = None,
    login_por_correo: BucketPolicy | None = None,
    login_por_ip: BucketPolicy | None = None,
    *,
    confiar_en_proxy: bool = False,
) -> HttpSecurity:
    return HttpSecurity(
        cookies=una_config_de_cookie(),
        rate_limits=politicas or RateLimitPolicies(authenticated=una_politica(), anonymous=una_politica()),
        login_by_email=login_por_correo or una_politica(),
        login_by_ip=login_por_ip or una_politica(),
        session_max_age_seconds=DURACION_DE_SESION,
        allowed_origins=origenes,
        trust_proxy=confiar_en_proxy,
    )


def cabecera_de_cookie(session_id: str, secreto: str = SECRETO_DE_PRUEBA) -> dict[str, str]:
    valor = quote(f"s:{sign(session_id, secreto)}", safe="")
    return {"Cookie": f"gestion_sid={valor}"}
