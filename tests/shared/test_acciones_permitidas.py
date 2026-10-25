import pytest

from app.enums.accion_incidencia import AccionIncidencia as A
from app.enums.categoria_incidencia import CategoriaIncidencia as C
from app.enums.estado_incidencia import EstadoIncidencia as E
from app.shared.acciones_permitidas import (
    CasoParaAcciones,
    acciones_permitidas,
    categorias_para_corregir,
    reglas_de_avisos,
)
from app.shared.permisos import PERMISOS_POR_ROL, ve_casos_sin_categoria


def caso(estado: E, categoria: C | None = C.RECLAMO, *, revisada: bool = False) -> CasoParaAcciones:
    return CasoParaAcciones(estado, categoria, revisada)


def test_un_gestor_ante_un_caso_clasificado_sin_revisar_puede_confirmar_o_corregir() -> None:
    assert acciones_permitidas(["GESTOR"], caso(E.CLASIFICADO)) == [A.CONFIRMAR, A.CORREGIR, A.ARCHIVAR]


def test_un_gestor_ante_un_caso_ya_revisado_puede_derivar_tomar_y_archivar() -> None:
    assert acciones_permitidas(["GESTOR"], caso(E.CLASIFICADO, revisada=True)) == [A.DERIVAR, A.TOMAR, A.ARCHIVAR]


def test_el_establecimiento_no_deriva() -> None:
    assert A.DERIVAR not in acciones_permitidas(["ESTABLECIMIENTO"], caso(E.CLASIFICADO, revisada=True))


def test_un_caso_derivado_se_toma_o_resuelve_y_uno_en_gestion_se_resuelve() -> None:
    assert acciones_permitidas(["GESTOR"], caso(E.DERIVADO)) == [A.TOMAR, A.RESOLVER, A.ARCHIVAR]
    assert acciones_permitidas(["GESTOR"], caso(E.EN_GESTION)) == [A.RESOLVER, A.ARCHIVAR]


def test_un_caso_archivado_solo_se_reabre() -> None:
    assert acciones_permitidas(["GESTOR"], caso(E.ARCHIVADO)) == [A.REABRIR]
    assert acciones_permitidas(["GESTOR"], caso(E.RESUELTO)) == []


def test_otrans_solo_actua_sobre_denuncias() -> None:
    assert A.CONFIRMAR in acciones_permitidas(["OTRANS"], caso(E.CLASIFICADO, C.DENUNCIA_CORRUPCION))
    assert acciones_permitidas(["OTRANS"], caso(E.CLASIFICADO, C.RECLAMO)) == []
    assert acciones_permitidas(["OTRANS"], caso(E.CLASIFICADO, None)) == []


def test_el_administrador_confirma_corrige_deriva_archiva_y_reabre_pero_no_toma_ni_resuelve() -> None:
    todas = {accion for estado in E for accion in acciones_permitidas(["ADMINISTRADOR"], caso(estado, revisada=True))}
    sin_revisar = acciones_permitidas(["ADMINISTRADOR"], caso(E.CLASIFICADO))

    assert todas == {A.DERIVAR, A.ARCHIVAR, A.REABRIR}
    assert sin_revisar == [A.CONFIRMAR, A.CORREGIR, A.ARCHIVAR]


def test_varios_roles_suman_sus_acciones_sin_repetir_y_en_el_orden_del_flujo() -> None:
    acciones = acciones_permitidas(["ESTABLECIMIENTO", "GESTOR"], caso(E.CLASIFICADO, revisada=True))

    assert acciones == [A.DERIVAR, A.TOMAR, A.ARCHIVAR]


def test_un_rol_desconocido_no_habilita_nada() -> None:
    assert acciones_permitidas(["NO_EXISTE", "DIRIS"], caso(E.CLASIFICADO)) == []


def test_corregir_desde_el_area_permite_pasar_a_denuncia_y_desde_otrans_cualquier_categoria() -> None:
    assert set(categorias_para_corregir(["GESTOR"], caso(E.CLASIFICADO))) == {
        C.QUEJA,
        C.RECLAMO,
        C.OTRO,
        C.DENUNCIA_CORRUPCION,
    }
    assert set(categorias_para_corregir(["OTRANS"], caso(E.CLASIFICADO, C.DENUNCIA_CORRUPCION))) == set(C)
    assert categorias_para_corregir(["GESTOR"], caso(E.EN_GESTION)) == []


def test_el_administrador_puede_corregir_a_cualquier_categoria() -> None:
    assert set(categorias_para_corregir(["ADMINISTRADOR"], caso(E.CLASIFICADO))) == set(C)


def test_el_administrador_recibe_aviso_de_todo_lo_abierto() -> None:
    assert reglas_de_avisos(["ADMINISTRADOR"]) is None
    assert reglas_de_avisos(["GESTOR", "ADMINISTRADOR"]) is None


def test_los_demas_roles_reciben_aviso_solo_de_lo_que_les_toca_atender() -> None:
    assert reglas_de_avisos(["GESTOR"]) == PERMISOS_POR_ROL["GESTOR"].acciones
    assert reglas_de_avisos(["GESTOR", "OTRANS"]) == (
        *PERMISOS_POR_ROL["GESTOR"].acciones,
        *PERMISOS_POR_ROL["OTRANS"].acciones,
    )
    assert reglas_de_avisos(["NO_EXISTE"]) == ()


@pytest.mark.parametrize(
    ("rol", "esperado"), [("ADMINISTRADOR", True), ("GESTOR", False), ("OTRANS", False), ("ESTABLECIMIENTO", False)]
)
def test_solo_el_administrador_ve_los_casos_sin_categoria(rol: str, esperado: bool) -> None:  # noqa: FBT001
    assert ve_casos_sin_categoria([rol]) is esperado
