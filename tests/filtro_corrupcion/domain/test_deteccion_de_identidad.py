import pytest

from app.enums.nivel_cargo import NivelCargo
from app.enums.tipo_contacto import TipoContacto
from app.enums.tipo_entidad import TipoEntidad
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.catalogo import catalogo_de_entidades
from app.filtro_corrupcion.domain.deteccion_de_identidad import (
    detectar_entidad,
    detectar_nombre_mencionado,
    detectar_titular,
    detectar_titular_nombrado,
    detectar_ubicacion,
    entidad_detectada_de,
    palabras_del_nombre_del_titular,
    referencia_de,
    titular_por_su_nombre,
)
from app.filtro_corrupcion.domain.normalizar_texto import tokenizar
from app.filtro_corrupcion.domain.tipos import (
    ActorDetectado,
    DestinoSiTitular,
    EntidadCatalogo,
    TitularCatalogo,
    TitularDetectado,
)

SIS = EntidadCatalogo("sis", "Seguro Integral de Salud", TipoEntidad.SIS, alias=("SIS",))
HOSPITAL_UNO = EntidadCatalogo("h1", "Hospital Nacional Uno", alias=("HN Uno",))
HOSPITAL_DOS = EntidadCatalogo("h2", "Hospital Nacional Uno Dos")
CON_TITULAR = EntidadCatalogo(
    "ct", "Entidad Titular", titular=TitularCatalogo("Directora General", "Ana María Torres Rojas")
)
OTRA_CON_TITULAR = EntidadCatalogo(
    "ot", "Otra Entidad", titular=TitularCatalogo("Jefe Institucional", "Ana Lopez Rojas")
)


def test_detecta_la_entidad_por_su_nombre_o_su_alias_y_devuelve_su_senal() -> None:
    hallada = detectar_entidad(tokenizar("me atendieron en el seguro integral de salud ayer"), (SIS,))

    assert hallada is not None
    assert hallada.entidad == entidad_detectada_de(SIS)
    assert (hallada.senal.frase, hallada.senal.tipo, hallada.senal.peso) == (
        "seguro integral de salud",
        TipoSenal.ENTIDAD,
        1,
    )
    assert detectar_entidad(tokenizar("trabaja en el sis desde hace anos"), (SIS,)) is not None


def test_sin_coincidencias_no_hay_entidad() -> None:
    assert detectar_entidad(tokenizar("el vecino camina por la calle"), (SIS,)) is None
    assert detectar_entidad(tokenizar("texto cualquiera"), ()) is None


def test_un_nombre_que_es_prefijo_de_otra_entidad_distinta_es_ambiguo_si_sigue_la_palabra_del_otro() -> None:
    palabras = tokenizar("fue al hospital nacional uno dos ayer")

    hallada = detectar_entidad(palabras, (HOSPITAL_UNO, HOSPITAL_DOS))

    assert hallada is not None
    assert hallada.catalogo.codigo == "h2"
    assert detectar_entidad(tokenizar("fue al hospital nacional uno"), (HOSPITAL_UNO, HOSPITAL_DOS)) is not None


def test_de_varias_coincidencias_gana_la_que_empieza_primero_y_luego_la_mas_larga() -> None:
    hallada = detectar_entidad(tokenizar("sis y hospital nacional uno"), (HOSPITAL_UNO, SIS))

    assert hallada is not None
    assert hallada.catalogo.codigo == "sis"


@pytest.mark.parametrize(
    ("nombre", "texto", "esperado"),
    [
        ("Ana María Torres Rojas", "dicen que ana maria torres rojas cobra", ["ana", "maria", "torres", "rojas"]),
        ("Ana María Torres Rojas", "la senora torres rojas me pidio", ["torres", "rojas"]),
        ("Ana María Torres Rojas", "solo ana ayer", None),
        ("Ana María Torres Rojas", "ana de torres rojas", ["ana", "torres", "rojas"]),
        ("Ana María Torres Rojas", "ana y luego rojas", None),
        ("Ana María Torres Rojas", "habla ana maria", None),
        (None, "ana maria", None),
        ("", "ana maria", None),
    ],
)
def test_el_nombre_del_titular_se_reconoce_por_palabras_seguidas(
    nombre: str | None, texto: str, esperado: list[str] | None
) -> None:
    assert palabras_del_nombre_del_titular(tokenizar(texto), nombre) == esperado


def test_dos_palabras_seguidas_identifican_solo_si_una_es_apellido() -> None:
    assert palabras_del_nombre_del_titular(tokenizar("ana maria"), "Ana María Torres Rojas") is None
    assert palabras_del_nombre_del_titular(tokenizar("maria torres"), "Ana María Torres Rojas") == ["maria", "torres"]


def test_el_titular_nombrado_necesita_ser_unico_entre_las_entidades() -> None:
    palabras = tokenizar("dicen que ana maria torres rojas pidio plata")

    unico = detectar_titular_nombrado(palabras, (CON_TITULAR, SIS), None)
    empate = detectar_titular_nombrado(tokenizar("ana rojas me cobro"), (CON_TITULAR, OTRA_CON_TITULAR), None)

    assert unico is not None
    assert (unico.catalogo.codigo, unico.frase) == ("ct", "ana maria torres rojas")
    assert empate is None


def test_con_una_entidad_ya_detectada_solo_se_busca_el_titular_de_esa_entidad() -> None:
    palabras = tokenizar("ana lopez rojas me cobro")

    assert detectar_titular_nombrado(palabras, (CON_TITULAR, OTRA_CON_TITULAR), CON_TITULAR) is None
    nombrado = detectar_titular_nombrado(palabras, (CON_TITULAR, OTRA_CON_TITULAR), OTRA_CON_TITULAR)
    assert nombrado is not None
    assert nombrado.catalogo.codigo == "ot"


def test_la_ubicacion_exige_que_la_entidad_este_activa_y_respeta_la_ambiguedad_con_el_establecimiento() -> None:
    entidades = catalogo_de_entidades()
    palabras = tokenizar("me paso en chosica el lunes")

    sin_establecimiento = detectar_ubicacion(palabras, entidades, establecimiento_conocido=False)
    con_establecimiento = detectar_ubicacion(palabras, entidades, establecimiento_conocido=True)
    sin_la_entidad = detectar_ubicacion(palabras, (SIS,), establecimiento_conocido=False)

    assert sin_establecimiento is not None
    assert (sin_establecimiento.ubicacion.zona, sin_establecimiento.ubicacion.codigo_entidad) == ("Chosica", "hjatch")
    assert (sin_establecimiento.senal.tipo, sin_establecimiento.senal.peso) == (TipoSenal.UBICACION, 1)
    assert con_establecimiento is None
    assert sin_la_entidad is None


def test_una_ubicacion_no_ambigua_se_detecta_aun_con_establecimiento_conocido() -> None:
    hallada = detectar_ubicacion(
        tokenizar("en huaycan pasa esto"), catalogo_de_entidades(), establecimiento_conocido=True
    )

    assert hallada is not None
    assert hallada.ubicacion.codigo_entidad == "hh"


def test_el_titular_solo_existe_si_el_actor_es_de_cargo_maximo() -> None:
    maximo = ActorDetectado("director general", NivelCargo.CARGO_MAXIMO)
    equivalente = ActorDetectado("jefa del sis", NivelCargo.CARGO_MAXIMO)

    assert detectar_titular(maximo, nombre_coincide=False) == TitularDetectado(
        "director general", es_equivalente_del_maximo=False, nombre_coincide=False
    )
    assert detectar_titular(equivalente, nombre_coincide=True) == TitularDetectado(
        "jefa del sis", es_equivalente_del_maximo=True, nombre_coincide=True
    )
    assert detectar_titular(ActorDetectado("medico", NivelCargo.PERSONAL), nombre_coincide=False) is None
    assert detectar_titular(None, nombre_coincide=True) is None


def test_el_titular_por_su_nombre_toma_el_cargo_del_catalogo_y_es_estandar_si_empieza_como_uno() -> None:
    estandar = titular_por_su_nombre(CON_TITULAR)
    equivalente = titular_por_su_nombre(
        EntidadCatalogo("x", "X", titular=TitularCatalogo("Presidenta Ejecutiva", "Ana Lopez"))
    )

    assert estandar == TitularDetectado("Directora General", es_equivalente_del_maximo=False, nombre_coincide=True)
    assert equivalente is not None
    assert equivalente.es_equivalente_del_maximo is True
    assert titular_por_su_nombre(SIS) is None
    assert titular_por_su_nombre(EntidadCatalogo("x", "X", titular=TitularCatalogo("", None))) is None


def test_la_referencia_de_derivacion_aplica_al_titular_solo_con_destino_y_titular() -> None:
    destino = DestinoSiTitular("A la PCM", None)
    entidad = EntidadCatalogo("x", "X", destino_si_titular=destino, contactos_disponibles=(TipoContacto.OCI,))
    titular = TitularDetectado("director general", es_equivalente_del_maximo=False, nombre_coincide=False)

    con = referencia_de(entidad, titular)
    sin_titular = referencia_de(entidad, None)
    sin_destino = referencia_de(SIS, titular)

    assert (con.codigo_entidad, con.contactos_disponibles, con.destino_si_titular, con.aplica_al_titular) == (
        "x",
        (TipoContacto.OCI,),
        destino,
        True,
    )
    assert sin_titular.aplica_al_titular is False
    assert (sin_destino.destino_si_titular, sin_destino.aplica_al_titular) == (None, False)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Me atendio Carlos Perez ayer", "Carlos Perez"),
        ("Dra. Ana Torres me cobro", "Ana Torres"),
        ("el Director Carlos Perez Soto me pidio", "Carlos Perez Soto"),
        ("Hablo la Directora General Maria Lopez", "Maria Lopez"),
        ("Hablo con Carlos", None),
        ("sin nombres aqui", None),
        ("Director General", None),
        ("el Medico Juan", None),
    ],
)
def test_el_nombre_mencionado_quita_los_cargos_del_inicio_y_pide_al_menos_dos_palabras(
    texto: str, esperado: str | None
) -> None:
    assert detectar_nombre_mencionado(texto) == esperado
