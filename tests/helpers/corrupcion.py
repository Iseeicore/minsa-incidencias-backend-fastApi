from dataclasses import replace
from typing import Any

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.origen_clasificacion import OrigenClasificacion
from app.filtro_corrupcion.domain.adaptar_clasificacion import AnalisisClasificado, adaptar_clasificacion
from app.filtro_corrupcion.domain.tipos import IdentidadDetectada, ResultadoCorrupcion
from app.filtro_corrupcion.domain.tipos_de_clasificacion import ResultadoClasificacion, ResumenCoincidencias

CAMPOS_DE_CLASIFICACION = frozenset(
    {
        "categoria",
        "reglas",
        "senales_queja_reclamo",
        "requiere_revision_humana",
        "revision_otrans",
        "origen",
        "coincidencias",
    }
)


def un_resultado_de_corrupcion(**cambios: Any) -> ResultadoCorrupcion:  # noqa: ANN401
    base: dict[str, Any] = {
        "aplica": True,
        "puntaje": 0,
        "certeza": CertezaCorrupcion.BAJA,
        "propuesta_corrupcion": False,
        "origen_propuesta": None,
        "senales": (),
        "actor": None,
        "nombre_mencionado": None,
        "entidad": None,
        "identidad": IdentidadDetectada(),
        "titular": None,
        "faltantes": (),
        "requiere_otrans": False,
        "referencia_derivacion": None,
        "requiere_segunda_opinion": False,
        "senal_sensible": None,
        "categoria_sugerida": None,
        "escalar_a_otrans": False,
        "version_reglas": "reglas-corrupcion-v1.3",
    }
    return ResultadoCorrupcion(**{**base, **cambios})


def un_resultado_de_clasificacion(**cambios: Any) -> ResultadoClasificacion:  # noqa: ANN401
    base: dict[str, Any] = {
        "categoria": CategoriaIncidencia.OTRO,
        "reglas": un_resultado_de_corrupcion(),
        "senales_queja_reclamo": (),
        "requiere_revision_humana": True,
        "revision_otrans": False,
        "origen": OrigenClasificacion.SIN_COINCIDENCIAS,
        "coincidencias": ResumenCoincidencias(EstadoCoincidencias.NO_CONSULTADA, None, None),
    }
    return ResultadoClasificacion(**{**base, **cambios})


def un_analisis_clasificado(**cambios: Any) -> AnalisisClasificado:  # noqa: ANN401
    resultado = un_resultado_de_clasificacion(**{k: v for k, v in cambios.items() if k in CAMPOS_DE_CLASIFICACION})
    analisis = adaptar_clasificacion(resultado)
    resto = {k: v for k, v in cambios.items() if k not in CAMPOS_DE_CLASIFICACION}
    return replace(analisis, **resto)
