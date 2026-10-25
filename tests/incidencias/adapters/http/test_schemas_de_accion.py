import pytest
from pydantic import ValidationError

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.adapters.http.schemas_de_accion import (
    ArchivoRequest,
    CasoEnviadoAOtransResponse,
    CorreccionRequest,
    DerivacionRequest,
    ReaperturaRequest,
    ResolucionRequest,
    ResultadoDeAccionResponse,
    SinDatosRequest,
    sin_nulo,
)
from app.incidencias.application.acciones import Archivar, Reabrir, Resolver
from app.incidencias.application.acciones_de_derivacion import Corregir, Derivar
from app.incidencias.application.armar_caso import detallar
from app.incidencias.domain.plazo import PlazosConfigurados
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion
from tests.helpers.builders import un_caso_consultado, una_sesion

TEXTO = "Texto de al menos diez"


def test_sin_nulo_deja_pasar_un_valor_y_rechaza_el_nulo() -> None:
    assert sin_nulo("a") == "a"
    with pytest.raises(ValueError, match="no puede ser nulo"):
        sin_nulo(None)


def test_un_cuerpo_vacio_o_con_campos_de_mas_se_acepta() -> None:
    assert SinDatosRequest.model_validate({"otro": 1}) == SinDatosRequest()


def test_la_correccion_traduce_la_categoria_del_contrato_a_la_del_dominio() -> None:
    accion = CorreccionRequest.model_validate({"categoria": "denuncia-corrupcion"}).a_accion()

    assert accion == Corregir(CategoriaIncidencia.DENUNCIA_CORRUPCION, None)


def test_la_correccion_recorta_la_descripcion_de_la_derivacion() -> None:
    accion = CorreccionRequest.model_validate({"categoria": "queja", "descripcionDerivacion": f"  {TEXTO} "}).a_accion()

    assert accion == Corregir(CategoriaIncidencia.QUEJA, TEXTO)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"categoria": "otra"},
        {"categoria": "queja", "descripcionDerivacion": None},
        {"categoria": "queja", "descripcionDerivacion": "corta"},
        {"categoria": "queja", "descripcionDerivacion": "x" * 2001},
    ],
)
def test_una_correccion_invalida_se_rechaza(cuerpo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CorreccionRequest.model_validate(cuerpo)


def test_la_derivacion_lleva_la_descripcion_y_el_area_opcional() -> None:
    cuerpo = {"areaDestino": " HOSP-01 ", "descripcionDerivacion": TEXTO}

    assert DerivacionRequest.model_validate(cuerpo).a_accion() == Derivar(TEXTO, "HOSP-01")
    assert DerivacionRequest.model_validate({"descripcionDerivacion": TEXTO}).a_accion() == Derivar(TEXTO, None)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"descripcionDerivacion": "corta"},
        {"descripcionDerivacion": TEXTO, "areaDestino": ""},
        {"descripcionDerivacion": TEXTO, "areaDestino": None},
        {"descripcionDerivacion": TEXTO, "areaDestino": "x" * 51},
    ],
)
def test_una_derivacion_invalida_se_rechaza(cuerpo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DerivacionRequest.model_validate(cuerpo)


def test_la_resolucion_exige_medidas_fundamento_y_resultado() -> None:
    cuerpo = {"medidasTomadas": TEXTO, "fundamento": f" {TEXTO} ", "resultado": "CERRADO"}

    assert ResolucionRequest.model_validate(cuerpo).a_accion() == Resolver(TEXTO, TEXTO, ResultadoResolucion.CERRADO)


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"medidasTomadas": TEXTO, "fundamento": TEXTO},
        {"medidasTomadas": "corta", "fundamento": TEXTO, "resultado": "ATENDIDO"},
        {"medidasTomadas": TEXTO, "fundamento": "x" * 4001, "resultado": "ATENDIDO"},
        {"medidasTomadas": TEXTO, "fundamento": TEXTO, "resultado": "OTRO"},
    ],
)
def test_una_resolucion_invalida_se_rechaza(cuerpo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ResolucionRequest.model_validate(cuerpo)


def test_el_archivo_manual_traduce_el_motivo_a_su_enum() -> None:
    accion = ArchivoRequest.model_validate({"motivo": "NO_CORRESPONDE", "detalle": TEXTO}).a_accion()

    assert accion == Archivar(MotivoArchivo.NO_CORRESPONDE, TEXTO)


@pytest.mark.parametrize("motivo", ["VENCIDA_SIN_ATENDER", "RESUELTA_VIGENCIA", "otro"])
def test_los_motivos_de_archivo_del_sistema_se_rechazan(motivo: str) -> None:
    with pytest.raises(ValidationError):
        ArchivoRequest.model_validate({"motivo": motivo, "detalle": TEXTO})


def test_el_detalle_del_archivo_exige_entre_10_y_2000_caracteres() -> None:
    with pytest.raises(ValidationError):
        ArchivoRequest.model_validate({"motivo": "NO_CORRESPONDE", "detalle": "corto"})
    with pytest.raises(ValidationError):
        ArchivoRequest.model_validate({"motivo": "NO_CORRESPONDE", "detalle": "x" * 2001})


def test_la_reapertura_lleva_el_motivo_recortado() -> None:
    assert ReaperturaRequest.model_validate({"motivo": f" {TEXTO} "}).a_accion() == Reabrir(TEXTO)


@pytest.mark.parametrize("cuerpo", [{}, {"motivo": "corto"}, {"motivo": "x" * 2001}])
def test_una_reapertura_invalida_se_rechaza(cuerpo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ReaperturaRequest.model_validate(cuerpo)


def test_el_resultado_sin_caso_se_serializa_con_caso_nulo() -> None:
    cuerpo = ResultadoDeAccionResponse.desde_dominio(ResultadoDeAccion("Listo.", None)).model_dump(
        by_alias=True, mode="json"
    )

    assert cuerpo == {"mensaje": "Listo.", "caso": None}


def test_el_resultado_con_caso_incluye_el_detalle() -> None:
    plazos = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
    detalle = detallar(un_caso_consultado(), una_sesion(), plazos, [], [])

    cuerpo = ResultadoDeAccionResponse.desde_dominio(ResultadoDeAccion("Listo.", detalle)).model_dump(
        by_alias=True, mode="json"
    )

    assert cuerpo["caso"]["codigo"] == "MINSA-2026-000001"


def test_el_caso_enviado_a_otrans_se_serializa_con_su_bandera() -> None:
    cuerpo = CasoEnviadoAOtransResponse.desde_dominio(CasoEnviadoAOtrans("MINSA-2026-000001")).model_dump(
        by_alias=True, mode="json"
    )

    assert cuerpo == {"codigo": "MINSA-2026-000001", "enviadoAOtrans": True}
