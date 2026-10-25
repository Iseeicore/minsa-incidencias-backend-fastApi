from functools import cache
from typing import TYPE_CHECKING, Any

from app.constants.catalogo_entidades import CATALOGO_DE_ENTIDADES, UBICACIONES_DE_ENTIDADES
from app.enums.tipo_contacto import TipoContacto
from app.enums.tipo_entidad import TipoEntidad
from app.filtro_corrupcion.domain.tipos import DestinoSiTitular, EntidadCatalogo, TitularCatalogo, UbicacionEntidad

if TYPE_CHECKING:
    from collections.abc import Mapping


def _titular(datos: Mapping[str, Any] | None) -> TitularCatalogo | None:
    return TitularCatalogo(datos["cargo"], datos.get("nombre")) if datos else None


def _destino(datos: Mapping[str, Any] | None) -> DestinoSiTitular | None:
    return DestinoSiTitular(datos["texto"], datos.get("entidadDestinoCodigo")) if datos else None


def _contactos_disponibles(contactos: Mapping[str, Any] | None) -> tuple[TipoContacto, ...]:
    if not contactos:
        return ()
    return tuple(tipo for tipo in TipoContacto if contactos.get(tipo.value) is not None)


def entidad_de_catalogo(datos: Mapping[str, Any]) -> EntidadCatalogo:
    tipo = datos.get("tipo")
    return EntidadCatalogo(
        codigo=datos["codigo"],
        nombre=datos["nombre"],
        tipo=TipoEntidad(tipo) if tipo is not None else None,
        alias=tuple(datos.get("alias") or ()),
        alias_derivados=tuple(datos.get("aliasDerivados") or ()),
        titular=_titular(datos.get("titular")),
        destino_si_titular=_destino(datos.get("destinoSiTitular")),
        contactos_disponibles=_contactos_disponibles(datos.get("contactos")),
    )


@cache
def catalogo_de_entidades() -> tuple[EntidadCatalogo, ...]:
    return tuple(entidad_de_catalogo(datos) for datos in CATALOGO_DE_ENTIDADES)


@cache
def ubicaciones_de_entidades() -> tuple[UbicacionEntidad, ...]:
    return tuple(
        UbicacionEntidad(datos["zona"], datos["codigoEntidad"], datos["ambiguaConEstablecimiento"])
        for datos in UBICACIONES_DE_ENTIDADES
    )
