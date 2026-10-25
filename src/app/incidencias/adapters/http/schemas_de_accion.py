from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import StringConstraints, field_validator

from app.constants.incidencias import (
    ARCHIVO_DETALLE_LONGITUD_MAXIMA,
    AREA_CODIGO_LONGITUD_MAXIMA,
    CATEGORIA_DESDE_API,
    DERIVACION_DESCRIPCION_LONGITUD_MAXIMA,
    REAPERTURA_MOTIVO_LONGITUD_MAXIMA,
    RESOLUCION_LONGITUD_MAXIMA,
    TEXTO_DE_REVISION_LONGITUD_MINIMA,
)
from app.constants.textos.incidencias import MENSAJE_VALOR_NULO
from app.enums.categoria_api import CategoriaApi
from app.enums.motivo_archivo import MotivoArchivo
from app.enums.resultado_resolucion import ResultadoResolucion
from app.incidencias.adapters.http.schemas import CasoDetalleResponse
from app.incidencias.application.acciones import Archivar, Reabrir, Resolver
from app.incidencias.application.acciones_de_derivacion import Corregir, Derivar
from app.shared.api_model import ApiModel

if TYPE_CHECKING:
    from app.incidencias.domain.resultado_de_accion import CasoEnviadoAOtrans, ResultadoDeAccion

DescripcionDeDerivacion = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=TEXTO_DE_REVISION_LONGITUD_MINIMA,
        max_length=DERIVACION_DESCRIPCION_LONGITUD_MAXIMA,
    ),
]
TextoDeResolucion = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=TEXTO_DE_REVISION_LONGITUD_MINIMA, max_length=RESOLUCION_LONGITUD_MAXIMA
    ),
]
DetalleDeArchivo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=TEXTO_DE_REVISION_LONGITUD_MINIMA, max_length=ARCHIVO_DETALLE_LONGITUD_MAXIMA
    ),
]
MotivoDeReapertura = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=TEXTO_DE_REVISION_LONGITUD_MINIMA,
        max_length=REAPERTURA_MOTIVO_LONGITUD_MAXIMA,
    ),
]
CodigoDeArea = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=AREA_CODIGO_LONGITUD_MAXIMA)
]
MotivoDeArchivoManual = Literal["DATOS_INSUFICIENTES", "NO_CORRESPONDE"]


def sin_nulo[T](valor: T | None) -> T:
    if valor is None:
        raise ValueError(MENSAJE_VALOR_NULO)
    return valor


class ResultadoDeAccionResponse(ApiModel):
    mensaje: str
    caso: CasoDetalleResponse | None

    @classmethod
    def desde_dominio(cls, resultado: ResultadoDeAccion) -> Self:
        caso = CasoDetalleResponse.desde_dominio(resultado.caso) if resultado.caso is not None else None
        return cls(mensaje=resultado.mensaje, caso=caso)


class CasoEnviadoAOtransResponse(ApiModel):
    codigo: str
    enviado_a_otrans: Literal[True]

    @classmethod
    def desde_dominio(cls, enviado: CasoEnviadoAOtrans) -> Self:
        return cls(codigo=enviado.codigo, enviado_a_otrans=True)


class SinDatosRequest(ApiModel):
    pass


class CorreccionRequest(ApiModel):
    categoria: CategoriaApi
    descripcion_derivacion: DescripcionDeDerivacion | None = None

    @field_validator("descripcion_derivacion", mode="after")
    @classmethod
    def _rechazar_nulo(cls, valor: str | None) -> str:
        return sin_nulo(valor)

    def a_accion(self) -> Corregir:
        return Corregir(CATEGORIA_DESDE_API[self.categoria], self.descripcion_derivacion)


class DerivacionRequest(ApiModel):
    area_destino: CodigoDeArea | None = None
    descripcion_derivacion: DescripcionDeDerivacion

    @field_validator("area_destino", mode="after")
    @classmethod
    def _rechazar_nulo(cls, valor: str | None) -> str:
        return sin_nulo(valor)

    def a_accion(self) -> Derivar:
        return Derivar(self.descripcion_derivacion, self.area_destino)


class ResolucionRequest(ApiModel):
    medidas_tomadas: TextoDeResolucion
    fundamento: TextoDeResolucion
    resultado: ResultadoResolucion

    def a_accion(self) -> Resolver:
        return Resolver(self.medidas_tomadas, self.fundamento, self.resultado)


class ArchivoRequest(ApiModel):
    motivo: MotivoDeArchivoManual
    detalle: DetalleDeArchivo

    def a_accion(self) -> Archivar:
        return Archivar(MotivoArchivo(self.motivo), self.detalle)


class ReaperturaRequest(ApiModel):
    motivo: MotivoDeReapertura

    def a_accion(self) -> Reabrir:
        return Reabrir(self.motivo)
