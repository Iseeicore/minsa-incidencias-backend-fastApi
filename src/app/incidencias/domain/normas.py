from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from app.constants.normas import FRAGMENTOS_DE_NORMAS

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class FragmentoNorma:
    id: str
    fuente: str
    referencia: str
    titulo: str
    tipo: str
    texto: str
    cita_automatica: bool
    motivo_sin_cita: str | None


def fragmento_de(dato: Mapping[str, str | bool]) -> FragmentoNorma:
    motivo = dato.get("motivo_sin_cita")
    return FragmentoNorma(
        id=cast("str", dato["id"]),
        fuente=cast("str", dato["fuente"]),
        referencia=cast("str", dato["referencia"]),
        titulo=cast("str", dato["titulo"]),
        tipo=cast("str", dato["tipo"]),
        texto=cast("str", dato["texto"]),
        cita_automatica=bool(dato["cita_automatica"]),
        motivo_sin_cita=cast("str", motivo) if motivo is not None else None,
    )


def fragmentos_por_id(datos: Iterable[Mapping[str, str | bool]] = FRAGMENTOS_DE_NORMAS) -> dict[str, FragmentoNorma]:
    fragmentos = (fragmento_de(dato) for dato in datos)
    return {fragmento.id: fragmento for fragmento in fragmentos}
