import pytest

from app.enums.accion_incidencia import AccionIncidencia
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_incidencia import EstadoIncidencia
from app.enums.tipo_area import TipoArea
from app.errors.datos_invalidos import DatosInvalidos
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.incidencias.application.acciones_de_derivacion import Corregir, Derivar
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion
from tests.helpers.builders import un_caso_consultado, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

GESTOR = una_sesion(roles=("GESTOR",))
OTRANS = una_sesion(roles=("OTRANS",))
SIN_ROL = una_sesion(roles=("DIRIS",))
DESCRIPCION = "Se devuelve al establecimiento de origen"
RECLAMO = un_caso_consultado()
DENUNCIA = un_caso_consultado(categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION)


async def test_corregir_cambia_la_categoria_del_caso() -> None:
    tx = IncidenciasEnMemoria()

    await Corregir(CategoriaIncidencia.QUEJA).aplicar(tx, GESTOR, RECLAMO)

    assert tx.llamadas == [("corregir", (RECLAMO.id, CategoriaIncidencia.QUEJA, None))]


async def test_corregir_guarda_la_descripcion_si_se_envia_sin_espacios_en_los_extremos() -> None:
    tx = IncidenciasEnMemoria()

    await Corregir(CategoriaIncidencia.QUEJA, f"  {DESCRIPCION}  ").aplicar(tx, GESTOR, RECLAMO)

    assert tx.llamadas == [("corregir", (RECLAMO.id, CategoriaIncidencia.QUEJA, DESCRIPCION))]


async def test_corregir_a_una_categoria_que_el_rol_no_alcanza_responde_403() -> None:
    with pytest.raises(SinPermiso, match=r"No puedes cambiar el caso a esa categoría\."):
        await Corregir(CategoriaIncidencia.QUEJA).aplicar(IncidenciasEnMemoria(), SIN_ROL, RECLAMO)


async def test_corregir_a_la_misma_categoria_responde_422() -> None:
    with pytest.raises(NoProcesable, match=r"La nueva categoría es igual a la actual\."):
        await Corregir(CategoriaIncidencia.RECLAMO).aplicar(IncidenciasEnMemoria(), GESTOR, RECLAMO)


async def test_otrans_que_devuelve_al_origen_valida_el_establecimiento_y_guarda_la_descripcion() -> None:
    tx = IncidenciasEnMemoria()
    tx.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1

    await Corregir(CategoriaIncidencia.QUEJA, DESCRIPCION).aplicar(tx, OTRANS, DENUNCIA)

    assert tx.llamadas == [
        ("area_receptora_por_id", (1, TipoArea.ESTABLECIMIENTO)),
        ("corregir", (DENUNCIA.id, CategoriaIncidencia.QUEJA, DESCRIPCION)),
    ]


async def test_otrans_que_devuelve_al_origen_sin_descripcion_responde_400() -> None:
    with pytest.raises(DatosInvalidos, match="entre 10 y 2000 caracteres"):
        await Corregir(CategoriaIncidencia.QUEJA).aplicar(IncidenciasEnMemoria(), OTRANS, DENUNCIA)


async def test_otrans_que_devuelve_al_origen_con_una_descripcion_corta_responde_400() -> None:
    with pytest.raises(DatosInvalidos, match="entre 10 y 2000 caracteres"):
        await Corregir(CategoriaIncidencia.QUEJA, "corta").aplicar(IncidenciasEnMemoria(), OTRANS, DENUNCIA)


async def test_otrans_que_devuelve_a_un_caso_sin_origen_responde_422() -> None:
    caso = un_caso_consultado(categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION, area_origen_id=None)

    with pytest.raises(NoProcesable, match="no tiene un destino vinculado válido"):
        await Corregir(CategoriaIncidencia.QUEJA, DESCRIPCION).aplicar(IncidenciasEnMemoria(), OTRANS, caso)


async def test_otrans_que_devuelve_a_un_origen_que_ya_no_recibe_responde_422() -> None:
    with pytest.raises(NoProcesable, match="no existe, está desactivada o no recibe este tipo de caso"):
        await Corregir(CategoriaIncidencia.QUEJA, DESCRIPCION).aplicar(IncidenciasEnMemoria(), OTRANS, DENUNCIA)


async def test_quien_tiene_otrans_y_corrige_a_denuncia_no_devuelve_al_origen() -> None:
    tx = IncidenciasEnMemoria()

    await Corregir(CategoriaIncidencia.DENUNCIA_CORRUPCION).aplicar(tx, una_sesion(roles=("OTRANS", "GESTOR")), RECLAMO)

    assert [nombre for nombre, _ in tx.llamadas] == ["corregir"]


def test_si_la_correccion_a_denuncia_saca_el_caso_de_la_vista_se_avisa_que_fue_a_otrans() -> None:
    resultado = Corregir(CategoriaIncidencia.DENUNCIA_CORRUPCION).sin_vista("MINSA-2026-000001")

    assert resultado == CasoEnviadoAOtrans("MINSA-2026-000001")


def test_si_otra_correccion_saca_el_caso_de_la_vista_el_mensaje_nombra_la_categoria() -> None:
    resultado = Corregir(CategoriaIncidencia.QUEJA).sin_vista("MINSA-2026-000001")

    assert resultado == ResultadoDeAccion(
        "Categoría corregida a Queja. El caso pasó al área correspondiente y ya no aparece en tu lista.", None
    )


def test_las_acciones_de_derivacion_declaran_su_tipo() -> None:
    assert Corregir.tipo == AccionIncidencia.CORREGIR
    assert Derivar.tipo == AccionIncidencia.DERIVAR


async def test_derivar_un_reclamo_va_al_establecimiento_de_origen() -> None:
    tx = IncidenciasEnMemoria()
    tx.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1

    await Derivar(f" {DESCRIPCION} ").aplicar(tx, GESTOR, RECLAMO)

    assert tx.llamadas == [
        ("area_receptora_por_id", (1, TipoArea.ESTABLECIMIENTO)),
        ("derivar", (RECLAMO.id, 1, DESCRIPCION)),
    ]


async def test_derivar_una_denuncia_permanece_en_el_area_otrans() -> None:
    tx = IncidenciasEnMemoria()
    caso = un_caso_consultado(
        categoria=CategoriaIncidencia.DENUNCIA_CORRUPCION, estado=EstadoIncidencia.CLASIFICADO, area_destino_id=9
    )
    tx.areas_por_id[(9, TipoArea.OTRANS)] = 9

    await Derivar(DESCRIPCION).aplicar(tx, OTRANS, caso)

    assert tx.llamadas == [("area_receptora_por_id", (9, TipoArea.OTRANS)), ("derivar", (caso.id, 9, DESCRIPCION))]


async def test_derivar_con_un_area_destino_que_coincide_con_la_vinculada_se_acepta() -> None:
    tx = IncidenciasEnMemoria()
    tx.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1
    tx.areas_por_codigo[("HOSP-01", TipoArea.ESTABLECIMIENTO)] = 1

    await Derivar(DESCRIPCION, "HOSP-01").aplicar(tx, GESTOR, RECLAMO)

    assert tx.llamadas[-1] == ("derivar", (RECLAMO.id, 1, DESCRIPCION))


async def test_derivar_a_un_area_distinta_de_la_vinculada_responde_422() -> None:
    tx = IncidenciasEnMemoria()
    tx.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1
    tx.areas_por_codigo[("HOSP-02", TipoArea.ESTABLECIMIENTO)] = 2

    with pytest.raises(NoProcesable, match="Solo se puede derivar al establecimiento vinculado al caso"):
        await Derivar(DESCRIPCION, "HOSP-02").aplicar(tx, GESTOR, RECLAMO)


async def test_derivar_a_un_codigo_de_area_inexistente_responde_422() -> None:
    tx = IncidenciasEnMemoria()
    tx.areas_por_id[(1, TipoArea.ESTABLECIMIENTO)] = 1

    with pytest.raises(NoProcesable, match="Solo se puede derivar al establecimiento vinculado al caso"):
        await Derivar(DESCRIPCION, "NO-EXISTE").aplicar(tx, GESTOR, RECLAMO)


async def test_derivar_un_caso_sin_destino_vinculado_responde_422() -> None:
    caso = un_caso_consultado(area_origen_id=None)

    with pytest.raises(NoProcesable, match="no tiene un destino vinculado válido"):
        await Derivar(DESCRIPCION).aplicar(IncidenciasEnMemoria(), GESTOR, caso)


async def test_derivar_a_un_area_que_ya_no_recibe_responde_422() -> None:
    with pytest.raises(NoProcesable, match="no existe, está desactivada o no recibe este tipo de caso"):
        await Derivar(DESCRIPCION).aplicar(IncidenciasEnMemoria(), GESTOR, RECLAMO)


async def test_derivar_con_una_descripcion_invalida_responde_400_sin_tocar_la_base() -> None:
    tx = IncidenciasEnMemoria()

    with pytest.raises(DatosInvalidos, match="entre 10 y 2000 caracteres"):
        await Derivar("corta").aplicar(tx, GESTOR, RECLAMO)

    assert tx.llamadas == []
