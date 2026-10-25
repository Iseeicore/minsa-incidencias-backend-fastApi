from dataclasses import FrozenInstanceError

import pytest

from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion


def test_el_resultado_de_una_accion_es_inmutable() -> None:
    with pytest.raises(FrozenInstanceError):
        ResultadoDeAccion("Listo.", None).mensaje = "Otro"  # type: ignore[misc]


def test_un_caso_enviado_a_otrans_lleva_solo_su_codigo() -> None:
    assert CasoEnviadoAOtrans("MINSA-2026-000001").codigo == "MINSA-2026-000001"
