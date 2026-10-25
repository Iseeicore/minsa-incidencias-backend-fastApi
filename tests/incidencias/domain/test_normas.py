from app.constants.normas import FRAGMENTOS_DE_NORMAS
from app.incidencias.domain.normas import FragmentoNorma, fragmento_de, fragmentos_por_id


def test_los_fragmentos_de_normas_son_los_29_del_node_con_identificadores_unicos() -> None:
    fragmentos = fragmentos_por_id()

    assert len(fragmentos) == len(FRAGMENTOS_DE_NORMAS) == 29
    assert next(iter(fragmentos)) == "ANEXO_C-I-a"
    assert list(fragmentos)[-1] == "AM-DEF-RECLAMO"


def test_un_fragmento_lleva_su_fuente_referencia_titulo_y_texto() -> None:
    fragmento = fragmentos_por_id()["AM-REQ-AUTORES"]

    assert fragmento.fuente == "AYUDA_MEMORIA_OTRANS"
    assert fragmento.referencia
    assert fragmento.titulo
    assert fragmento.texto
    assert fragmento.cita_automatica is True


def test_algunos_fragmentos_explican_por_que_no_se_citan_solos() -> None:
    con_motivo = [fragmento for fragmento in fragmentos_por_id().values() if fragmento.motivo_sin_cita is not None]

    assert con_motivo
    assert all(fragmento.cita_automatica is False for fragmento in con_motivo)


def test_un_fragmento_sin_motivo_lo_deja_nulo() -> None:
    fragmento = fragmento_de(
        {
            "id": "X",
            "fuente": "F",
            "referencia": "R",
            "titulo": "T",
            "tipo": "FALTA",
            "texto": "Texto",
            "cita_automatica": True,
        }
    )

    assert fragmento == FragmentoNorma("X", "F", "R", "T", "FALTA", "Texto", cita_automatica=True, motivo_sin_cita=None)


def test_se_pueden_indexar_otros_datos() -> None:
    datos: list[dict[str, str | bool]] = [
        {
            "id": "A",
            "fuente": "F",
            "referencia": "R",
            "titulo": "T",
            "tipo": "X",
            "texto": "t",
            "cita_automatica": False,
        }
    ]

    assert list(fragmentos_por_id(datos)) == ["A"]
