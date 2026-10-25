import pytest

from app.errors.datos_invalidos import DatosInvalidos
from app.errors.no_encontrado import NoEncontrado
from app.shared.cursor import PosicionPorNombre, encode_uuid_cursor
from app.usuarios.adapters.http.consulta import consulta_de_usuarios, identificador_de_usuario

ANA = "11111111-1111-4111-8111-111111111111"


def test_los_valores_por_defecto_piden_cincuenta_sin_filtros() -> None:
    consulta = consulta_de_usuarios(50, None, "", "")

    assert (consulta.limite, consulta.despues_de, consulta.texto, consulta.area) == (50, None, None, None)


def test_el_texto_y_el_area_vacios_se_vuelven_nulos_y_los_llenos_pasan() -> None:
    consulta = consulta_de_usuarios(10, None, "ana", "HOSP-01")

    assert (consulta.limite, consulta.texto, consulta.area) == (10, "ana", "HOSP-01")


def test_un_cursor_valido_se_decodifica() -> None:
    posicion = PosicionPorNombre("Ana", ANA)

    assert consulta_de_usuarios(10, encode_uuid_cursor(posicion), "", "").despues_de == posicion


def test_un_cursor_alterado_es_un_error_de_validacion_con_el_mensaje_del_contrato() -> None:
    with pytest.raises(DatosInvalidos) as capturado:
        consulta_de_usuarios(10, "###", "", "")

    assert capturado.value.details == [{"path": "cursor", "message": "El cursor no es válido."}]


def test_un_identificador_en_minusculas_pasa() -> None:
    assert identificador_de_usuario(ANA) == ANA


@pytest.mark.parametrize(
    "identificador", ["", "no-es-uuid", ANA.replace("-", ""), "0B9F8C9E-7D0A-4F5B-9A3C-1E2D3C4B5A69"]
)
def test_un_identificador_que_no_es_uuid_en_minusculas_es_404(identificador: str) -> None:
    with pytest.raises(NoEncontrado):
        identificador_de_usuario(identificador)
