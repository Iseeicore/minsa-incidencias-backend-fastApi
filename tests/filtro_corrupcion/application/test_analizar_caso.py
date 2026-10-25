from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.estado_coincidencias import EstadoCoincidencias
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.filtro_corrupcion.application.analizar_caso import analizar_caso
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion
from app.filtro_corrupcion.domain.tipos_de_clasificacion import CandidatoCoincidencia

CORRUPCION = "El director del hospital me pidio una coima de 100 soles para operarme y no me dio recibo"
QUEJA = "El personal fue grosero y prepotente conmigo en la ventanilla del hospital"


async def test_una_denuncia_se_escribe_como_corrupcion_con_la_version_del_motor() -> None:
    caso = await analizar_caso(CORRUPCION, ContextoEvaluacion(), None)

    assert caso.decision.categoria == CategoriaIncidencia.DENUNCIA_CORRUPCION
    assert (caso.decision.motivo, caso.decision.confianza) == (MotivoDeEscritura.REGLAS, 65.0)
    assert caso.version == "reglas-corrupcion-v1.3+coincidencias-v1"
    assert caso.reglas.puntaje == 7
    assert caso.senales.decision.categoria_escrita == CategoriaIncidencia.DENUNCIA_CORRUPCION


async def test_los_antecedentes_se_buscan_con_el_texto_del_caso() -> None:
    consultas: list[str] = []

    async def buscar(texto: str) -> list[CandidatoCoincidencia]:
        consultas.append(texto)
        return [CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.9)]

    caso = await analizar_caso(QUEJA, ContextoEvaluacion(establecimiento_conocido=True), buscar)

    assert consultas == [QUEJA]
    assert caso.decision.categoria == CategoriaIncidencia.QUEJA
    assert caso.senales.clasificacion.coincidencias.estado == EstadoCoincidencias.CORROBORADA


async def test_una_denuncia_de_corrupcion_no_consulta_antecedentes() -> None:
    consultas: list[str] = []

    async def buscar(texto: str) -> list[CandidatoCoincidencia]:
        consultas.append(texto)
        return [CandidatoCoincidencia(CategoriaIncidencia.QUEJA, 0.9)]

    caso = await analizar_caso(CORRUPCION, ContextoEvaluacion(), buscar)

    assert consultas == []
    assert caso.senales.clasificacion.coincidencias.estado == EstadoCoincidencias.NO_CONSULTADA
