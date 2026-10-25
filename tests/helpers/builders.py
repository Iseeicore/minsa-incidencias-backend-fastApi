from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.shared.http_security import HttpSecurity
from app.shared.rate_limit import RateLimitPolicies
from app.shared.sesion import SesionActual
from app.shared.session_cookie import SessionCookieConfig
from app.shared.token_bucket import BucketPolicy

SECRETO_DE_PRUEBA = "secreto-de-prueba-0123456789-abcdefghijklmnop"
SECRETO_ANTERIOR = "secreto-anterior-9876543210-zyxwvutsrqponmlk"
CAPACIDAD_HOLGADA = 1000
VENTANA_DE_PRUEBA = 60


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


def una_sesion(correo: str = "gestor@minsa.gob.pe") -> SesionActual:
    return SesionActual(
        sesion_id="6f1c2c9e-7a49-4a39-9d44-2f6e9d6a0001",
        usuario_id="0b7a5c1e-31a2-4b7e-8c0d-5f4f5c2d0001",
        correo=correo,
        nombre_completo="Gestor de Prueba",
        roles=("GESTOR",),
    )


def una_politica(capacidad: int = CAPACIDAD_HOLGADA, ventana: int = VENTANA_DE_PRUEBA) -> BucketPolicy:
    return BucketPolicy(capacity=capacidad, window_seconds=ventana)


def una_config_de_cookie(*, produccion: bool = False) -> SessionCookieConfig:
    return SessionCookieConfig(secrets=(SECRETO_DE_PRUEBA, SECRETO_ANTERIOR), production=produccion)


def una_seguridad(
    origenes: tuple[str, ...] = (),
    politicas: RateLimitPolicies | None = None,
    *,
    confiar_en_proxy: bool = False,
) -> HttpSecurity:
    return HttpSecurity(
        cookies=una_config_de_cookie(),
        rate_limits=politicas or RateLimitPolicies(authenticated=una_politica(), anonymous=una_politica()),
        allowed_origins=origenes,
        trust_proxy=confiar_en_proxy,
    )
