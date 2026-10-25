from dataclasses import FrozenInstanceError

import pytest

from app.enums.rol_codigo import RolCodigo
from app.usuarios.domain.pedidos import (
    CambiosDeUsuario,
    ConsultaUsuarios,
    DatosNuevoUsuario,
    FiltrosDeUsuarios,
    NuevoUsuarioFila,
    RestriccionDeArea,
    UsuarioConClave,
)
from tests.helpers.builders import un_usuario_gestionado


def test_los_valores_por_defecto_no_filtran_ni_cambian_nada() -> None:
    assert ConsultaUsuarios(limite=5) == ConsultaUsuarios(limite=5, despues_de=None, texto=None, area=None)
    assert FiltrosDeUsuarios() == FiltrosDeUsuarios(texto=None, area_codigo=None, restriccion_de_area=None)
    assert CambiosDeUsuario() == CambiosDeUsuario(None, None, None, None)
    assert DatosNuevoUsuario("A", "a@m.pe", RolCodigo.GESTOR).area is None


def test_los_pedidos_son_inmutables() -> None:
    with pytest.raises(FrozenInstanceError):
        RestriccionDeArea(1).area_id = 2  # type: ignore[misc]


def test_la_clave_inicial_viaja_junto_al_usuario_creado() -> None:
    usuario = un_usuario_gestionado()

    assert UsuarioConClave(usuario, "abc").usuario is usuario
    assert NuevoUsuarioFila("A", "a@m.pe", "hash", None).area_id is None
