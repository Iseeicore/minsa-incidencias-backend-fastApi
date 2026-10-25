from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from app.constants.incidencias import CATEGORIA_ETIQUETA
from app.constants.textos.incidencias import (
    MENSAJE_AREA_DESTINO_INVALIDA,
    MENSAJE_CATEGORIA_NO_PERMITIDA,
    MENSAJE_DESCRIPCION_DERIVACION_INVALIDA,
    MENSAJE_DESTINO_NO_VINCULADO,
    MENSAJE_MISMA_CATEGORIA,
    MENSAJE_SIN_DESTINO_DE_DERIVACION,
    mensaje_categoria_corregida_fuera_de_vista,
)
from app.enums.accion_incidencia import AccionIncidencia
from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.rol_codigo import RolCodigo
from app.enums.tipo_area import TipoArea
from app.errors.datos_invalidos import DatosInvalidos
from app.errors.no_procesable import NoProcesable
from app.errors.sin_permiso import SinPermiso
from app.incidencias.application.acciones import Accion
from app.incidencias.domain.descripcion_de_derivacion import descripcion_de_derivacion, descripcion_si_se_envia
from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion
from app.shared.acciones_permitidas import CasoParaAcciones, categorias_para_corregir

if TYPE_CHECKING:
    from app.incidencias.application.ports import IncidenciaTransaction
    from app.incidencias.domain.caso_consultado import CasoConsultado
    from app.shared.sesion import SesionActual


async def _validar_origen(tx: IncidenciaTransaction, caso: CasoConsultado) -> None:
    if caso.area_origen_id is None:
        raise NoProcesable(MENSAJE_SIN_DESTINO_DE_DERIVACION)
    if await tx.area_receptora_por_id(caso.area_origen_id, TipoArea.ESTABLECIMIENTO) is None:
        raise NoProcesable(MENSAJE_AREA_DESTINO_INVALIDA)


async def _area_de_derivacion(tx: IncidenciaTransaction, caso: CasoConsultado, area_destino: str | None) -> int:
    sensible = caso.categoria == CategoriaIncidencia.DENUNCIA_CORRUPCION
    por_defecto = caso.area_destino_id if sensible else caso.area_origen_id
    if por_defecto is None:
        raise NoProcesable(MENSAJE_SIN_DESTINO_DE_DERIVACION)
    tipo = TipoArea.OTRANS if sensible else TipoArea.ESTABLECIMIENTO
    area_id = await tx.area_receptora_por_id(por_defecto, tipo)
    if area_id is None:
        raise NoProcesable(MENSAJE_AREA_DESTINO_INVALIDA)
    if area_destino and await tx.area_receptora_por_codigo(area_destino, tipo) != area_id:
        raise NoProcesable(MENSAJE_DESTINO_NO_VINCULADO)
    return area_id


@dataclass(frozen=True, slots=True)
class Corregir(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.CORREGIR
    categoria: CategoriaIncidencia
    descripcion_derivacion: str | None = None

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:
        alcanzables = categorias_para_corregir(
            sesion.roles, CasoParaAcciones(caso.estado, caso.categoria, caso.revisada)
        )
        if self.categoria not in alcanzables:
            raise SinPermiso(MENSAJE_CATEGORIA_NO_PERMITIDA)
        if self.categoria == caso.categoria:
            raise NoProcesable(MENSAJE_MISMA_CATEGORIA)
        devuelve_a_origen = (
            RolCodigo.OTRANS in sesion.roles and self.categoria != CategoriaIncidencia.DENUNCIA_CORRUPCION
        )
        descripcion = descripcion_si_se_envia(self.descripcion_derivacion)
        if devuelve_a_origen and descripcion is None:
            raise DatosInvalidos(MENSAJE_DESCRIPCION_DERIVACION_INVALIDA)
        if devuelve_a_origen:
            await _validar_origen(tx, caso)
        await tx.corregir(caso.id, self.categoria, descripcion)

    def sin_vista(self, codigo: str) -> ResultadoDeAccion | CasoEnviadoAOtrans:
        if self.categoria == CategoriaIncidencia.DENUNCIA_CORRUPCION:
            return CasoEnviadoAOtrans(codigo)
        return ResultadoDeAccion(mensaje_categoria_corregida_fuera_de_vista(CATEGORIA_ETIQUETA[self.categoria]), None)


@dataclass(frozen=True, slots=True)
class Derivar(Accion):
    tipo: ClassVar[AccionIncidencia] = AccionIncidencia.DERIVAR
    descripcion_derivacion: str
    area_destino: str | None = None

    async def aplicar(self, tx: IncidenciaTransaction, sesion: SesionActual, caso: CasoConsultado) -> None:  # noqa: ARG002
        descripcion = descripcion_de_derivacion(self.descripcion_derivacion)
        area_id = await _area_de_derivacion(tx, caso, self.area_destino)
        await tx.derivar(caso.id, area_id, descripcion)
