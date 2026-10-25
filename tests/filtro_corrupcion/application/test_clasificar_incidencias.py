import pytest

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.informacion_faltante_ia import InformacionFaltanteIa
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.errors.consulta_de_cola_fallida import ConsultaDeColaFallida
from app.filtro_corrupcion.application.clasificar_incidencias import (
    AlarmaSinClasificar,
    ClasificadorIncidencias,
    ColaVacia,
    FalloDeClasificacion,
    IncidenciaClasificada,
    ResumenDeCola,
    consultar_alarma_sin_clasificar,
    vaciar_cola,
)
from app.filtro_corrupcion.domain.cola_de_clasificacion import CasoPendiente, FilaAlarma
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia
from tests.helpers.clasificador_en_memoria import AlmacenDelClasificador

CORRUPCION = "El director del hospital Dos de Mayo me pidio una coima de 100 soles para operarme"
SIN_ENTIDAD = "El director del hospital me pidio una coima de 100 soles para operarme y no me dio recibo"
QUEJA = "El personal fue grosero y prepotente conmigo en la ventanilla del hospital"
OTRO = "Buenas tardes quisiera saber el horario de atencion del hospital"


class _ErrorDeBase(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("error de la base")
        self.orig = type("Original", (), {"sqlstate": sqlstate})()


def _caso(numero: int, descripcion: str, establecimiento: str | None = None) -> CasoPendiente:
    return CasoPendiente(f"id-{numero}", f"MINSA-2026-{numero:06d}", descripcion, establecimiento)


def _clasificador(almacen: AlmacenDelClasificador, **opciones: object) -> ClasificadorIncidencias:
    return ClasificadorIncidencias(almacen, **opciones)  # type: ignore[arg-type]


async def test_una_denuncia_se_clasifica_y_guarda_su_analisis_con_el_area_mencionada() -> None:
    almacen = AlmacenDelClasificador([_caso(1, CORRUPCION)])
    almacen.areas["hndm"] = 77

    salida = await _clasificador(almacen).clasificar_siguiente()

    assert salida == IncidenciaClasificada(
        "MINSA-2026-000001", CategoriaIncidencia.DENUNCIA_CORRUPCION, 65.0, MotivoDeEscritura.REGLAS
    )
    [analisis] = almacen.analisis
    assert (analisis.incidencia_id, analisis.version_reglas, analisis.puntaje) == ("id-1", "reglas-corrupcion-v1.3", 8)
    assert (analisis.cargo_mencionado, analisis.area_mencionada_id, analisis.nombre_mencionado) == (
        "director del hospital",
        77,
        None,
    )
    [categoria] = almacen.categorias
    assert (categoria.incidencia_id, categoria.categoria, categoria.version) == (
        "id-1",
        CategoriaIncidencia.DENUNCIA_CORRUPCION,
        "reglas-corrupcion-v1.3+coincidencias-v1",
    )
    assert almacen.cola == []


async def test_el_area_mencionada_queda_vacia_si_el_catalogo_no_la_tiene() -> None:
    almacen = AlmacenDelClasificador([_caso(1, CORRUPCION)])

    await _clasificador(almacen).clasificar_siguiente()

    assert almacen.analisis[0].area_mencionada_id is None


async def test_un_caso_sin_entidad_en_el_texto_no_busca_area() -> None:
    almacen = AlmacenDelClasificador([_caso(1, SIN_ENTIDAD)])
    almacen.areas["hndm"] = 77

    await _clasificador(almacen).clasificar_siguiente()

    assert almacen.analisis[0].area_mencionada_id is None


async def test_la_clasificacion_corre_con_el_actor_del_clasificador() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO)])

    await _clasificador(almacen).clasificar_siguiente()

    assert almacen.actores == ["sistema:clasificador"]


async def test_saber_el_establecimiento_del_caso_quita_la_entidad_de_lo_que_falta() -> None:
    sin = AlmacenDelClasificador([_caso(1, SIN_ENTIDAD)])
    con = AlmacenDelClasificador([_caso(1, SIN_ENTIDAD, "Hospital de Prueba")])

    await _clasificador(sin).clasificar_siguiente()
    await _clasificador(con).clasificar_siguiente()

    assert InformacionFaltanteIa.ENTIDAD_O_UNIDAD in sin.analisis[0].senales.informacion_faltante
    assert InformacionFaltanteIa.ENTIDAD_O_UNIDAD not in con.analisis[0].senales.informacion_faltante


async def test_los_antecedentes_se_buscan_con_el_caso_y_pueden_decidir_la_categoria() -> None:
    almacen = AlmacenDelClasificador([_caso(1, QUEJA)])
    almacen.candidatos = [CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.9)]

    salida = await _clasificador(almacen).clasificar_siguiente()

    assert almacen.busquedas == [("id-1", QUEJA)]
    assert isinstance(salida, IncidenciaClasificada)
    assert salida.categoria == CategoriaIncidencia.QUEJA


async def test_sin_casos_pendientes_la_cola_esta_vacia_y_la_consulta_lleva_abandonados_y_limite() -> None:
    almacen = AlmacenDelClasificador()

    salida = await _clasificador(almacen, solo_casos=("id-9",)).clasificar_siguiente()

    assert salida == ColaVacia()
    assert almacen.consultas == [((), ("id-9",))]
    assert almacen.analisis == []


async def test_si_falla_el_guardado_el_caso_sigue_pendiente_y_el_siguiente_intento_lo_clasifica() -> None:
    almacen = AlmacenDelClasificador([_caso(1, CORRUPCION)])
    almacen.falla_al_guardar = _ErrorDeBase("42703")
    clasificador = _clasificador(almacen)

    primero = await clasificador.clasificar_siguiente()
    almacen.falla_al_guardar = None
    segundo = await clasificador.clasificar_siguiente()

    assert primero == FalloDeClasificacion("id-1", "MINSA-2026-000001", 1, "42703", abandonado=False)
    assert isinstance(segundo, IncidenciaClasificada)
    assert len(almacen.analisis) == 1
    assert clasificador.abandonados == []


async def test_el_codigo_del_error_es_el_nombre_de_la_clase_si_no_es_un_error_de_la_base() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO)])
    almacen.falla_al_guardar = ValueError("falla simulada")

    salida = await _clasificador(almacen).clasificar_siguiente()

    assert isinstance(salida, FalloDeClasificacion)
    assert salida.codigo_de_error == "ValueError"
    assert "falla simulada" not in repr(salida)


async def test_un_caso_roto_se_abandona_tras_el_maximo_de_intentos_y_no_tapa_a_los_demas() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO), _caso(2, QUEJA)])
    almacen.falla_al_guardar = ValueError("roto")
    clasificador = _clasificador(almacen, maximo_intentos=2)

    primero = await clasificador.clasificar_siguiente()
    segundo = await clasificador.clasificar_siguiente()
    almacen.falla_al_guardar = None
    tercero = await clasificador.clasificar_siguiente()

    assert [primero, segundo] == [
        FalloDeClasificacion("id-1", "MINSA-2026-000001", 1, "ValueError", abandonado=False),
        FalloDeClasificacion("id-1", "MINSA-2026-000001", 2, "ValueError", abandonado=True),
    ]
    assert clasificador.abandonados == ["id-1"]
    assert isinstance(tercero, IncidenciaClasificada)
    assert tercero.codigo == "MINSA-2026-000002"
    assert almacen.consultas[-1][0] == ("id-1",)


async def test_si_falla_la_consulta_de_la_cola_el_error_se_propaga_como_cola_fallida() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO)])
    almacen.falla_al_consultar_la_cola = RuntimeError("sin base")

    with pytest.raises(ConsultaDeColaFallida) as error:
        await _clasificador(almacen).clasificar_siguiente()

    assert isinstance(error.value.__cause__, RuntimeError)


async def test_vaciar_la_cola_cuenta_clasificadas_fallos_abandonadas_y_denuncias() -> None:
    almacen = AlmacenDelClasificador([_caso(1, CORRUPCION), _caso(2, QUEJA), _caso(3, OTRO)])
    clasificador = _clasificador(almacen)

    resumen = await vaciar_cola(clasificador)

    assert resumen == ResumenDeCola(clasificadas=3, fallos=0, abandonadas=0, a_otrans=1)


async def test_vaciar_la_cola_cuenta_los_fallos_y_las_abandonadas() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO), _caso(2, QUEJA)])
    almacen.falla_al_guardar = ValueError("roto")

    resumen = await vaciar_cola(_clasificador(almacen, maximo_intentos=1))

    assert resumen == ResumenDeCola(clasificadas=0, fallos=2, abandonadas=2, a_otrans=0)


async def test_vaciar_la_cola_respeta_el_maximo_de_casos() -> None:
    almacen = AlmacenDelClasificador([_caso(1, OTRO), _caso(2, QUEJA), _caso(3, OTRO)])

    resumen = await vaciar_cola(_clasificador(almacen), maximo_casos=2)

    assert resumen.clasificadas == 2
    assert len(almacen.cola) == 1


async def test_la_alarma_se_enciende_con_casos_atrasados_y_trae_el_mas_antiguo() -> None:
    almacen = AlmacenDelClasificador()
    almacen.fila_de_alarma = FilaAlarma(2, 61.5, ("MINSA-2026-000001", "MINSA-2026-000002"))

    alarma = await consultar_alarma_sin_clasificar(almacen)

    assert alarma == AlarmaSinClasificar(2, 61.5, ("MINSA-2026-000001", "MINSA-2026-000002"))
    assert alarma.activa is True
    assert almacen.consultas_de_alarma == [(10, 10)]


@pytest.mark.parametrize("fila", [None, FilaAlarma(0, None, ()), FilaAlarma(0, 4.0, ())])
async def test_sin_casos_atrasados_la_alarma_queda_apagada_y_sin_minutos(fila: FilaAlarma | None) -> None:
    almacen = AlmacenDelClasificador()
    almacen.fila_de_alarma = fila

    alarma = await consultar_alarma_sin_clasificar(almacen, minutos=5)

    assert (alarma.activa, alarma.minutos_del_mas_antiguo, alarma.codigos) == (False, None, ())
    assert almacen.consultas_de_alarma == [(5, 10)]
