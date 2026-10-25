from app.catalogos.domain.plazo_de_categoria import PlazoDeCategoria
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.shared.sesion import SesionActual


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
