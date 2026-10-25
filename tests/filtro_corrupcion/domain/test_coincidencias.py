import pytest

from app.errors.clase_de_lexico_desconocida import ClaseDeLexicoDesconocida
from app.filtro_corrupcion.domain.coincidencias import (
    Coincidencia,
    EntradaPonderada,
    ItemCompilado,
    buscar_coincidencias,
    compilar_plantilla,
    crear_indice,
    es_clase,
    expandir_plantilla,
    resolver_choques,
)


def _entrada(grupo: str, peso: int = 1, familia: str | None = None) -> EntradaPonderada:
    return EntradaPonderada(peso=peso, grupo=grupo, familia=familia)


def _item(
    plantilla: str, grupo: str | None = None, peso: int = 1, familia: str | None = None
) -> ItemCompilado[EntradaPonderada]:
    [patron] = compilar_plantilla(plantilla)
    return ItemCompilado(patron, _entrada(grupo or plantilla, peso, familia))


def _buscar(palabras: list[str], *items: ItemCompilado[EntradaPonderada]) -> list[Coincidencia[EntradaPonderada]]:
    return buscar_coincidencias(palabras, crear_indice(list(items)))


@pytest.mark.parametrize(
    ("plantilla", "esperado"),
    [
        ("sin grupos", ("sin grupos",)),
        ("{a|b} c", ("a c", "b c")),
        ("{a|b} {c|d}", ("a c", "a d", "b c", "b d")),
        ("x {a|}", ("x a", "x ")),
        ("{a{b|c}", ("{ab", "{ac")),
        ("abierta {a|b", ("abierta {a|b",)),
        ("cerrada a|b}", ("cerrada a|b}",)),
        ("{uno} y {dos}", ("uno y dos",)),
        ("", ("",)),
    ],
)
def test_expandir_plantilla_reemplaza_cada_grupo_por_sus_opciones_en_orden(
    plantilla: str, esperado: tuple[str, ...]
) -> None:
    assert expandir_plantilla(plantilla) == esperado


def test_compilar_normaliza_las_palabras_deja_las_clases_y_el_hueco_y_cuenta_una_variante_por_opcion() -> None:
    patrones = compilar_plantilla("Me {PIDIÓ|pidieron}  ~ @verbo_cobro")

    assert patrones == [("me", "pidio", "~", "@verbo_cobro"), ("me", "pidieron", "~", "@verbo_cobro")]


def test_compilar_una_clase_que_no_existe_falla_con_su_nombre() -> None:
    with pytest.raises(ClaseDeLexicoDesconocida, match="@no_existe"):
        compilar_plantilla("hola @no_existe")


def test_solo_lo_que_empieza_con_arroba_es_una_clase() -> None:
    assert es_clase("@verbo_cobro") is True
    assert es_clase("verbo") is False


def test_una_frase_se_encuentra_con_su_inicio_y_su_fin() -> None:
    [coincidencia] = _buscar(["dijo", "me", "pidio", "plata", "ayer"], _item("me pidio plata"))

    assert (coincidencia.inicio, coincidencia.fin) == (1, 4)


def test_una_frase_incompleta_o_al_final_del_texto_no_coincide() -> None:
    assert _buscar(["me", "pidio"], _item("me pidio plata")) == []
    assert _buscar(["me", "dio", "plata"], _item("me pidio plata")) == []


def test_el_hueco_admite_de_cero_a_tres_palabras() -> None:
    item = _item("me ~ plata")

    assert [c.fin for c in _buscar(["me", "plata"], item)] == [2]
    assert [c.fin for c in _buscar(["me", "a", "b", "c", "plata"], item)] == [5]
    assert _buscar(["me", "a", "b", "c", "d", "plata"], item) == []


def test_una_clase_calza_cualquier_palabra_de_la_clase() -> None:
    item = _item("@verbo_cobro plata")

    assert len(_buscar(["cobran", "plata"], item)) == 1
    assert len(_buscar(["pidio", "plata"], item)) == 1
    assert _buscar(["camina", "plata"], item) == []


def test_los_montos_se_saltan_salvo_que_el_patron_pida_el_monto() -> None:
    assert [c.fin for c in _buscar(["me", "monto", "pidio"], _item("me pidio"))] == [3]
    assert _buscar(["me", "monto", "pidio"], _item("me monto pidio"), _item("me pidio plata")) != []
    assert [c.fin for c in _buscar(["me", "monto"], _item("me monto"))] == [2]


def test_el_primer_elemento_no_salta_montos() -> None:
    assert _buscar(["monto", "me", "pidio"], _item("me pidio"))[0].inicio == 1


def test_las_coincidencias_salen_en_orden_de_posicion_y_luego_de_declaracion() -> None:
    primera = _item("pidio plata", "a")
    segunda = _item("pidio", "b")

    coincidencias = _buscar(["pidio", "plata", "pidio"], primera, segunda)

    assert [(c.entrada.grupo, c.inicio, c.fin) for c in coincidencias] == [("a", 0, 2), ("b", 0, 1), ("b", 2, 3)]


def test_un_patron_que_empieza_con_hueco_o_vacio_no_se_indexa() -> None:
    assert crear_indice([ItemCompilado(("~", "plata"), _entrada("g")), ItemCompilado((), _entrada("h"))]) == {}


def test_las_clases_traen_los_candidatos_de_su_clase_despues_de_los_de_la_palabra() -> None:
    literal = _item("cobran plata", "literal")
    clase = _item("@verbo_cobro plata", "clase")

    coincidencias = _buscar(["cobran", "plata"], clase, literal)

    assert [c.entrada.grupo for c in coincidencias] == ["literal", "clase"]


def _coincidencia(  # noqa: PLR0913
    grupo: str, inicio: int, fin: int, *, peso: int = 1, patron: tuple[str, ...] = ("x",), familia: str | None = None
) -> Coincidencia[EntradaPonderada]:
    return Coincidencia(_entrada(grupo, peso, familia), patron, inicio, fin)


def test_de_un_mismo_grupo_solo_queda_la_primera_coincidencia() -> None:
    primera = _coincidencia("g", 0, 2)
    segunda = _coincidencia("g", 5, 7)

    assert resolver_choques([primera, segunda]) == [primera]


def test_si_dos_frases_se_pisan_gana_la_de_mas_peso_y_luego_la_mas_larga() -> None:
    debil = _coincidencia("a", 0, 3, peso=1)
    fuerte = _coincidencia("b", 2, 5, peso=3)
    larga = _coincidencia("c", 2, 7, peso=3)

    assert resolver_choques([debil, fuerte]) == [fuerte]
    assert resolver_choques([fuerte, larga]) == [larga]


def test_el_peso_negativo_compite_por_su_valor_absoluto() -> None:
    negativa = _coincidencia("n", 0, 2, peso=-3)
    media = _coincidencia("m", 1, 3, peso=2)

    assert resolver_choques([media, negativa]) == [negativa]


def test_frases_que_no_se_pisan_se_conservan_en_orden_de_posicion() -> None:
    tarde = _coincidencia("b", 5, 7)
    pronto = _coincidencia("a", 0, 2)

    assert resolver_choques([tarde, pronto]) == [pronto, tarde]


def test_una_frase_contenida_en_otra_con_sus_mismas_palabras_se_descarta() -> None:
    externa = _coincidencia("e", 0, 4, peso=3, patron=("me", "pidio", "plata"))
    interna = _coincidencia("i", 1, 3, peso=2, patron=("pidio", "plata"))

    assert resolver_choques([externa, interna]) == [externa]


def test_una_frase_contenida_pero_con_palabras_distintas_tambien_choca_si_se_pisan_sin_ser_subconjunto() -> None:
    externa = _coincidencia("e", 0, 4, peso=3, patron=("me", "pidio", "plata"))
    interna = _coincidencia("i", 1, 3, peso=2, patron=("otra", "cosa"))

    assert resolver_choques([externa, interna]) == [externa, interna]


def test_dos_frases_de_la_misma_familia_que_se_pisan_chocan_aunque_una_este_dentro() -> None:
    externa = _coincidencia("e", 0, 4, peso=3, patron=("a", "b", "c"), familia="cobro")
    interna = _coincidencia("i", 1, 3, peso=2, patron=("x", "y"), familia="cobro")

    assert resolver_choques([externa, interna]) == [externa]


def test_si_no_hay_coincidencias_no_hay_nada_que_resolver() -> None:
    assert resolver_choques([]) == []
