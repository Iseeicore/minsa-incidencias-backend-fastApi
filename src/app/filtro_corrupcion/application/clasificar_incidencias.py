from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from app.constants.actores import ACTOR_SISTEMA_CLASIFICADOR
from app.constants.clasificacion import (
    ALARMA_CODIGOS_MAXIMOS,
    MAXIMO_INTENTOS_POR_CASO,
    UMBRAL_ALARMA_SIN_CLASIFICAR_MINUTOS,
)
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.errors.consulta_de_cola_fallida import ConsultaDeColaFallida
from app.filtro_corrupcion.application.analizar_caso import analizar_caso
from app.filtro_corrupcion.domain.cola_de_clasificacion import AnalisisAGuardar, CategoriaAEscribir
from app.filtro_corrupcion.domain.tipos import ContextoEvaluacion

if TYPE_CHECKING:
    from app.enums.motivo_de_escritura import MotivoDeEscritura
    from app.filtro_corrupcion.application.analizar_caso import CasoAnalizado
    from app.filtro_corrupcion.application.ports import (
        AlarmaReader,
        ClasificadorTransaction,
        ClasificadorUnitOfWork,
    )
    from app.filtro_corrupcion.domain.cola_de_clasificacion import CasoPendiente


@dataclass(frozen=True, slots=True)
class IncidenciaClasificada:
    codigo: str
    categoria: CategoriaIncidencia
    confianza: float
    motivo: MotivoDeEscritura


@dataclass(frozen=True, slots=True)
class ColaVacia:
    pass


@dataclass(frozen=True, slots=True)
class FalloDeClasificacion:
    id: str
    codigo: str
    intentos: int
    codigo_de_error: str
    abandonado: bool


type SalidaDeClasificar = IncidenciaClasificada | ColaVacia | FalloDeClasificacion


@dataclass(frozen=True, slots=True)
class ResumenDeCola:
    clasificadas: int = 0
    fallos: int = 0
    abandonadas: int = 0
    a_otrans: int = 0


@dataclass(frozen=True, slots=True)
class AlarmaSinClasificar:
    atrasados: int
    minutos_del_mas_antiguo: float | None
    codigos: tuple[str, ...]

    @property
    def activa(self) -> bool:
        return self.atrasados > 0


def _codigo_del_error(error: Exception) -> str:
    estado = getattr(getattr(error, "orig", error), "sqlstate", None)
    return estado if isinstance(estado, str) else type(error).__name__


class ClasificadorIncidencias:
    def __init__(
        self,
        unidad: ClasificadorUnitOfWork,
        *,
        maximo_intentos: int = MAXIMO_INTENTOS_POR_CASO,
        solo_casos: tuple[str, ...] | None = None,
    ) -> None:
        self._unidad = unidad
        self._maximo_intentos = maximo_intentos
        self._solo_casos = solo_casos
        self._fallos: dict[str, int] = {}

    @property
    def abandonados(self) -> list[str]:
        return [id_ for id_, intentos in self._fallos.items() if intentos >= self._maximo_intentos]

    async def clasificar_siguiente(self) -> SalidaDeClasificar:
        pendiente: CasoPendiente | None = None
        try:
            async with self._unidad.begin(ACTOR_SISTEMA_CLASIFICADOR) as transaccion:
                pendiente = await transaccion.siguiente_pendiente(tuple(self.abandonados), self._solo_casos)
                if pendiente is None:
                    return ColaVacia()
                clasificada = await self._clasificar(transaccion, pendiente)
        except Exception as error:
            if pendiente is None:
                raise ConsultaDeColaFallida from error
            return self._registrar_fallo(pendiente, error)
        self._fallos.pop(pendiente.id, None)
        return clasificada

    async def _clasificar(
        self, transaccion: ClasificadorTransaction, pendiente: CasoPendiente
    ) -> IncidenciaClasificada:
        contexto = ContextoEvaluacion(establecimiento_conocido=pendiente.establecimiento is not None)
        caso = await analizar_caso(
            pendiente.descripcion, contexto, partial(transaccion.buscar_coincidencias, pendiente.id)
        )
        await self._guardar(transaccion, pendiente, caso)
        return IncidenciaClasificada(
            codigo=pendiente.codigo,
            categoria=caso.decision.categoria,
            confianza=caso.decision.confianza,
            motivo=caso.decision.motivo,
        )

    async def _guardar(
        self, transaccion: ClasificadorTransaction, pendiente: CasoPendiente, caso: CasoAnalizado
    ) -> None:
        reglas = caso.reglas
        entidad = reglas.entidad.codigo if reglas.entidad is not None else None
        area_id = await transaccion.area_mencionada(entidad) if entidad is not None else None
        await transaccion.registrar_analisis(
            AnalisisAGuardar(
                incidencia_id=pendiente.id,
                version_reglas=reglas.version_reglas,
                puntaje=reglas.puntaje,
                senales=caso.senales,
                cargo_mencionado=reglas.actor.cargo if reglas.actor is not None else None,
                area_mencionada_id=area_id,
                nombre_mencionado=reglas.nombre_mencionado,
            )
        )
        await transaccion.actualizar_categoria(
            CategoriaAEscribir(
                incidencia_id=pendiente.id,
                categoria=caso.decision.categoria,
                confianza=caso.decision.confianza,
                version=caso.version,
            )
        )

    def _registrar_fallo(self, pendiente: CasoPendiente, error: Exception) -> FalloDeClasificacion:
        intentos = self._fallos.get(pendiente.id, 0) + 1
        self._fallos[pendiente.id] = intentos
        return FalloDeClasificacion(
            id=pendiente.id,
            codigo=pendiente.codigo,
            intentos=intentos,
            codigo_de_error=_codigo_del_error(error),
            abandonado=intentos >= self._maximo_intentos,
        )


async def vaciar_cola(clasificador: ClasificadorIncidencias, maximo_casos: int | None = None) -> ResumenDeCola:
    clasificadas = fallos = abandonadas = a_otrans = 0
    while maximo_casos is None or clasificadas + fallos < maximo_casos:
        salida = await clasificador.clasificar_siguiente()
        if isinstance(salida, ColaVacia):
            break
        if isinstance(salida, FalloDeClasificacion):
            fallos += 1
            abandonadas += salida.abandonado
            continue
        clasificadas += 1
        a_otrans += salida.categoria == CategoriaIncidencia.DENUNCIA_CORRUPCION
    return ResumenDeCola(clasificadas, fallos, abandonadas, a_otrans)


async def consultar_alarma_sin_clasificar(
    lector: AlarmaReader, minutos: int = UMBRAL_ALARMA_SIN_CLASIFICAR_MINUTOS
) -> AlarmaSinClasificar:
    fila = await lector.alarma_sin_clasificar(minutos, ALARMA_CODIGOS_MAXIMOS)
    atrasados = fila.atrasados if fila is not None else 0
    return AlarmaSinClasificar(
        atrasados=atrasados,
        minutos_del_mas_antiguo=fila.minutos if fila is not None and atrasados > 0 else None,
        codigos=fila.codigos if fila is not None else (),
    )
