from typing import Any

from app.constants.datos_estaticos import cargar_datos
from app.enums.nivel_cargo import NivelCargo

_LEXICO: dict[str, Any] = cargar_datos("lexico_corrupcion.json")
_CLASES: dict[str, list[str]] = cargar_datos("clases_de_lexico.json")

FRASES_FUERTES = tuple[str, ...](_LEXICO["frases_fuertes"])
FRASES_MEDIAS = tuple[str, ...](_LEXICO["frases_medias"])
FRASES_DEBILES = tuple[str, ...](_LEXICO["frases_debiles"])
FRASES_NEGATIVAS_DECISIVAS = tuple[str, ...](_LEXICO["frases_negativas_decisivas"])
FRASES_NEGATIVAS_LEVES = tuple[str, ...](_LEXICO["frases_negativas_leves"])
FRASES_FUERTES_DE_COBRO = tuple[str, ...](_LEXICO["frases_fuertes_de_cobro"])
FRASES_MEDIAS_DE_COBRO = tuple[str, ...](_LEXICO["frases_medias_de_cobro"])
FRASES_DEBILES_DE_COBRO = tuple[str, ...](_LEXICO["frases_debiles_de_cobro"])
FRASES_DE_ACOSO = tuple[str, ...](_LEXICO["frases_de_acoso"])
FRASES_DE_PRUEBAS = tuple[str, ...](_LEXICO["frases_de_pruebas"])
PALABRAS_QUE_ENGANAN = frozenset[str](_LEXICO["palabras_que_enganan"])
PALABRAS_QUE_NIEGAN = frozenset[str](_LEXICO["palabras_que_niegan"])
NEGADORES_DE_COBRO = frozenset[str](_LEXICO["negadores_de_cobro"])
NEGADORES_DENTRO_DEL_COBRO = frozenset[str](_LEXICO["negadores_dentro_del_cobro"])
INICIOS_QUE_YA_NIEGAN = frozenset[str](_LEXICO["inicios_que_ya_niegan"])
PLANTILLAS_DE_LA_FAMILIA_DE_COBRO = frozenset[str](_LEXICO["plantillas_de_la_familia_de_cobro"])
PALABRAS_DE_JEFATURA = frozenset[str](_LEXICO["palabras_de_jefatura"])
CARGOS = tuple((cargo["plantilla"], NivelCargo(cargo["nivel"])) for cargo in _LEXICO["cargos"])
CLASES_DE_LEXICO = {nombre: frozenset(palabras) for nombre, palabras in _CLASES.items()}
