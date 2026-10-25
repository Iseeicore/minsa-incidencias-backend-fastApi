from typing import Any

from app.enums.certeza_corrupcion import CertezaCorrupcion
from app.filtro_corrupcion.domain.tipos import IdentidadDetectada, ResultadoCorrupcion


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
