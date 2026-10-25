from app.enums.tipo_contacto import TipoContacto
from app.enums.tipo_entidad import TipoEntidad
from app.filtro_corrupcion.domain.catalogo import (
    catalogo_de_entidades,
    entidad_de_catalogo,
    ubicaciones_de_entidades,
)


def test_el_catalogo_oficial_trae_37_entidades_con_codigos_unicos() -> None:
    codigos = [entidad.codigo for entidad in catalogo_de_entidades()]

    assert len(codigos) == len(set(codigos)) == 37
    assert codigos[:2] == ["minsa", "sis"]


def test_una_entidad_del_catalogo_trae_tipo_alias_titular_destino_y_contactos() -> None:
    minsa = next(entidad for entidad in catalogo_de_entidades() if entidad.codigo == "minsa")

    assert (minsa.nombre, minsa.tipo, minsa.alias) == ("Ministerio de Salud", TipoEntidad.MINISTERIO, ("MINSA",))
    assert minsa.titular is not None
    assert (minsa.titular.cargo, minsa.titular.nombre) == ("Ministro de Salud", None)
    assert minsa.destino_si_titular is not None
    assert minsa.destino_si_titular.entidad_destino_codigo is None
    assert minsa.contactos_disponibles == (TipoContacto.OCI, TipoContacto.INTEGRIDAD, TipoContacto.PROCURADOR)


def test_los_contactos_disponibles_siguen_el_orden_del_enum_y_omiten_los_nulos() -> None:
    entidad = entidad_de_catalogo(
        {
            "codigo": "x",
            "nombre": "X",
            "contactos": {"PROCURADOR": [{"nombre": "a"}], "OCI": None, "INTEGRIDAD": [{"nombre": "b"}]},
        }
    )

    assert entidad.contactos_disponibles == (TipoContacto.INTEGRIDAD, TipoContacto.PROCURADOR)


def test_una_entidad_con_solo_codigo_y_nombre_no_trae_nada_mas() -> None:
    entidad = entidad_de_catalogo({"codigo": "x", "nombre": "X", "alias": None, "aliasDerivados": None})

    assert (entidad.tipo, entidad.alias, entidad.alias_derivados) == (None, (), ())
    assert (entidad.titular, entidad.destino_si_titular, entidad.contactos_disponibles) == (None, None, ())


def test_las_ubicaciones_indican_si_se_confunden_con_un_establecimiento() -> None:
    ubicaciones = {ubicacion.zona: ubicacion for ubicacion in ubicaciones_de_entidades()}

    assert len(ubicaciones) == 18
    assert ubicaciones["Chosica"].ambigua_con_establecimiento is True
    assert (ubicaciones["SJL"].codigo_entidad, ubicaciones["SJL"].ambigua_con_establecimiento) == ("hsjl", False)
