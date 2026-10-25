from app.enums.nivel_cargo import NivelCargo
from app.enums.tipo_senal import TipoSenal
from app.filtro_corrupcion.domain.lexico import (
    entradas_de_cargo,
    indice_de_acoso,
    indice_de_cargos,
    indice_de_entidades,
    indice_de_pruebas,
    indice_de_senales,
    indice_de_ubicaciones,
    palabras_de_cargo,
    verbos_de_cobro,
)
from app.filtro_corrupcion.domain.tipos import EntidadCatalogo


def _items(indice: dict) -> list:  # type: ignore[type-arg]
    return [
        item
        for grupo in indice.values()
        for _, item in [*grupo.generales, *(i for lista in grupo.por_segundo.values() for i in lista)]
    ]


def _patrones(indice: dict) -> set[tuple[str, ...]]:  # type: ignore[type-arg]
    return {item.patron for item in _items(indice)}


def test_el_indice_de_senales_compila_decenas_de_miles_de_patrones_agrupados_por_primera_palabra() -> None:
    indice = indice_de_senales()

    assert len(indice) > 100
    assert ("me", "pidio", "plata", "para") in _patrones(indice)
    assert "@verbo_cobro" in indice


def test_las_palabras_sueltas_que_enganan_no_se_compilan_como_patron() -> None:
    patrones = _patrones(indice_de_senales())

    assert ("denuncia",) not in patrones
    assert ("cobro",) not in patrones


def test_las_senales_de_cobro_son_negables_y_comparten_familia() -> None:
    entradas = {
        item.entrada.grupo: item.entrada
        for item in _items(indice_de_senales())
        if item.entrada.tipo == TipoSenal.FUERTE
    }
    cobro = entradas["me {pidio|pidieron|pide|piden} {dinero|plata} para"]

    assert (cobro.negable, cobro.familia, cobro.peso) == (False, "cobro", 3)


def test_los_cargos_se_compilan_con_su_nivel_y_peso_de_actor() -> None:
    entradas = entradas_de_cargo()
    niveles = {item.entrada.nivel for item in entradas}

    assert niveles == set(NivelCargo)
    assert {item.entrada.peso for item in entradas} == {1}
    assert entradas_de_cargo() is entradas
    assert "director" in indice_de_cargos()


def test_las_palabras_de_cargo_incluyen_los_articulos_y_tratamientos_pero_no_el_hueco() -> None:
    palabras = palabras_de_cargo()

    assert {"director", "ministra", "el", "dra", "sr"} <= palabras
    assert "~" not in palabras


def test_los_verbos_de_cobro_suman_cobro_y_solicito_a_la_clase() -> None:
    verbos = verbos_de_cobro()

    assert {"pide", "cobran", "cobro", "solicito"} <= verbos


def test_los_indices_de_acoso_y_pruebas_no_pesan() -> None:
    assert "acoso" in indice_de_acoso()
    assert "prueba" in indice_de_pruebas()
    assert all(item.entrada.peso == 0 for item in _items(indice_de_pruebas()))


def test_el_indice_de_ubicaciones_tokeniza_cada_zona() -> None:
    indice = indice_de_ubicaciones()

    assert {"huaycan", "chosica", "sjl", "san", "santa"} <= set(indice)


def test_el_indice_de_entidades_incluye_nombre_alias_y_alias_derivados_y_se_reutiliza() -> None:
    entidad = EntidadCatalogo("x", "Entidad Uno", alias=("EU",), alias_derivados=("la entidad",))
    vacia = EntidadCatalogo("y", "!!!")

    indice = indice_de_entidades((entidad, vacia))

    assert [item.patron for item in indice.entradas] == [("entidad", "uno"), ("eu",), ("la", "entidad")]
    assert {"entidad", "eu", "la"} == set(indice.indice)
    assert indice_de_entidades((entidad, vacia)) is indice
