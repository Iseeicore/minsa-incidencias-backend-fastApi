from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class DiaDeEvolucion:
    dia: str
    recibidos: int
    resueltos: int


@dataclass(frozen=True, slots=True)
class CuboDeEvolucion:
    desde: str
    recibidos: int
    resueltos: int


def agrupar_en_cubos(dias: Sequence[DiaDeEvolucion], dias_por_cubo: int) -> list[CuboDeEvolucion]:
    paso = max(dias_por_cubo, 1)
    cubos: list[CuboDeEvolucion] = []
    for indice, dia in enumerate(dias):
        if indice % paso == 0 or not cubos:
            cubos.append(CuboDeEvolucion(dia.dia, dia.recibidos, dia.resueltos))
        else:
            ultimo = cubos[-1]
            cubos[-1] = CuboDeEvolucion(
                ultimo.desde, ultimo.recibidos + dia.recibidos, ultimo.resueltos + dia.resueltos
            )
    return cubos
