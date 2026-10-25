import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.resultado_resolucion import ResultadoResolucion
from app.errors.no_encontrado import NoEncontrado
from app.errors.sin_permiso import SinPermiso
from app.incidencias.application.acciones import Confirmar, Resolver, Tomar
from app.incidencias.application.acciones_de_derivacion import Corregir
from app.incidencias.application.ejecutar_accion import EjecutarAccion
from app.incidencias.domain.plazo import PlazosConfigurados
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion
from tests.helpers.builders import un_caso_consultado, una_evidencia, una_sesion
from tests.helpers.incidencias_en_memoria import IncidenciasEnMemoria

PLAZOS = PlazosConfigurados(vigencia_dias=30, aviso_horas=48)
GESTOR = una_sesion(roles=("GESTOR",))
CODIGO = "MINSA-2026-000001"


def _ejecutor(tx: IncidenciasEnMemoria) -> EjecutarAccion:
    return EjecutarAccion(tx, tx, PLAZOS)


async def test_ejecuta_la_accion_con_el_actor_de_la_sesion_y_devuelve_el_caso_actualizado() -> None:
    tx = IncidenciasEnMemoria([un_caso_consultado()], evidencias=[una_evidencia()])

    resultado = await _ejecutor(tx).execute(GESTOR, CODIGO, Confirmar())

    assert isinstance(resultado, ResultadoDeAccion)
    assert resultado.mensaje == "Categoría confirmada."
    assert resultado.caso is not None
    assert resultado.caso.resumen.codigo == CODIGO
    assert [e.id for e in resultado.caso.evidencias] == ["0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69"]
    assert tx.actores == ["usuario:gestor@minsa.gob.pe"]
    assert [nombre for nombre, _ in tx.llamadas][:2] == ["buscar_bloqueando", "confirmar"]


async def test_un_caso_que_no_existe_o_no_es_visible_responde_404_y_no_aplica_nada() -> None:
    tx = IncidenciasEnMemoria()

    with pytest.raises(NoEncontrado, match=r"El caso solicitado no existe\."):
        await _ejecutor(tx).execute(GESTOR, CODIGO, Confirmar())

    assert [nombre for nombre, _ in tx.llamadas] == ["buscar_bloqueando"]


async def test_una_accion_que_el_estado_actual_no_permite_responde_403_con_su_mensaje() -> None:
    tx = IncidenciasEnMemoria([un_caso_consultado()])
    accion = Resolver("a" * 10, "b" * 10, ResultadoResolucion.ATENDIDO)

    with pytest.raises(SinPermiso, match=r"No puedes resolver este caso\."):
        await _ejecutor(tx).execute(GESTOR, CODIGO, accion)

    assert [nombre for nombre, _ in tx.llamadas] == ["buscar_bloqueando"]


async def test_el_mensaje_de_cada_accion_no_permitida_nombra_esa_accion() -> None:
    tx = IncidenciasEnMemoria([un_caso_consultado(revisada=False)])

    with pytest.raises(SinPermiso, match=r"No puedes tomar este caso en gestión\."):
        await _ejecutor(tx).execute(GESTOR, CODIGO, Tomar())


async def test_si_el_caso_sale_de_la_vista_responde_el_mensaje_sin_caso() -> None:
    tx = IncidenciasEnMemoria([un_caso_consultado()])
    tx.ocultar_al_cerrar = True

    resultado = await _ejecutor(tx).execute(GESTOR, CODIGO, Corregir(CategoriaIncidencia.QUEJA))

    assert resultado == ResultadoDeAccion(
        "Categoría corregida a Queja. El caso pasó al área correspondiente y ya no aparece en tu lista.", None
    )


async def test_si_una_correccion_a_denuncia_saca_el_caso_de_la_vista_avisa_que_fue_a_otrans() -> None:
    tx = IncidenciasEnMemoria([un_caso_consultado()])
    tx.ocultar_al_cerrar = True

    resultado = await _ejecutor(tx).execute(GESTOR, CODIGO, Corregir(CategoriaIncidencia.DENUNCIA_CORRUPCION))

    assert resultado == CasoEnviadoAOtrans(CODIGO)
