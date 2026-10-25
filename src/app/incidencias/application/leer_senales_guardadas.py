from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.enums.categoria_incidencia import CategoriaIncidencia
from app.enums.grupo_cita import GrupoCita
from app.enums.informacion_faltante_ia import InformacionFaltanteIa
from app.enums.motivo_de_escritura import MotivoDeEscritura
from app.enums.tipo_contacto import TipoContacto
from app.enums.variante_ia import VarianteIa
from app.incidencias.domain.analisis import (
    CitaGuardada,
    DecisionGuardada,
    DestinoSiTitular,
    FichaDeDerivacion,
    ModeloGuardado,
    NormasGuardadas,
    Numero,
    SenalDeAnalisis,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

type Objeto = Mapping[str, object]

GRUPOS_DE_CITA = (GrupoCita.SUPUESTO, GrupoCita.PROCEDIMIENTO)


@dataclass(frozen=True, slots=True)
class SenalesGuardadas:
    senales: tuple[SenalDeAnalisis, ...] = ()
    explicacion: str | None = None
    informacion_faltante: tuple[InformacionFaltanteIa, ...] = ()
    ficha_derivacion: FichaDeDerivacion | None = None
    normas: NormasGuardadas | None = None
    decision: DecisionGuardada | None = None
    modelo: ModeloGuardado | None = None


def _objeto(valor: object) -> Objeto | None:
    return valor if isinstance(valor, dict) else None


def _texto(valor: object) -> str | None:
    return valor if isinstance(valor, str) else None


def _booleano(valor: object) -> bool:
    return valor if isinstance(valor, bool) else False


def _numero(valor: object) -> Numero | None:
    return valor if isinstance(valor, int | float) and not isinstance(valor, bool) else None


def _enumerado[E: Enum](tipo: type[E], valor: object, permitidos: tuple[E, ...] | None = None) -> E | None:
    if not isinstance(valor, str):
        return None
    try:
        miembro = tipo(valor)
    except ValueError:
        return None
    return miembro if permitidos is None or miembro in permitidos else None


def _lista_de_textos(valor: object) -> tuple[str, ...]:
    if not isinstance(valor, list) or not all(isinstance(item, str) for item in valor):
        return ()
    return tuple(valor)


def _senales(valor: object) -> tuple[SenalDeAnalisis, ...]:
    if not isinstance(valor, list):
        return ()
    senales: list[SenalDeAnalisis] = []
    for item in valor:
        objeto = _objeto(item)
        frase = _texto(objeto.get("frase")) if objeto is not None else None
        tipo = _texto(objeto.get("tipo")) if objeto is not None else None
        peso = _numero(objeto.get("peso")) if objeto is not None else None
        if frase is None or tipo is None or peso is None:
            return ()
        senales.append(SenalDeAnalisis(frase, tipo, peso))
    return tuple(senales)


def _faltantes(valor: object) -> tuple[InformacionFaltanteIa, ...]:
    if not isinstance(valor, list):
        return ()
    faltantes = [_enumerado(InformacionFaltanteIa, item) for item in valor]
    return () if None in faltantes else tuple(faltante for faltante in faltantes if faltante is not None)


def _cita(valor: object) -> CitaGuardada | None:
    objeto = _objeto(valor)
    if objeto is None:
        return None
    fragmento_id = _texto(objeto.get("fragmentoId"))
    referencia = _texto(objeto.get("referencia"))
    grupo = _enumerado(GrupoCita, objeto.get("grupo"), GRUPOS_DE_CITA)
    if fragmento_id is None or referencia is None or grupo is None:
        return None
    return CitaGuardada(fragmento_id, referencia, grupo, _lista_de_textos(objeto.get("senalesQueLaMotivan")))


def _citas(valor: object) -> tuple[CitaGuardada, ...]:
    if not isinstance(valor, list):
        return ()
    citas = [_cita(item) for item in valor]
    return () if None in citas else tuple(cita for cita in citas if cita is not None)


def _normas(valor: object) -> NormasGuardadas | None:
    objeto = _objeto(valor)
    if objeto is None:
        return None
    version = _texto(objeto.get("version"))
    if version is None or ("etiqueta" in objeto and _texto(objeto["etiqueta"]) is None):
        return None
    return NormasGuardadas(
        version=version,
        transcripcion_anexo_c_cotejada=_booleano(objeto.get("transcripcionAnexoCCotejada")),
        sin_supuesto_identificado=_booleano(objeto.get("sinSupuestoIdentificado")),
        citas=_citas(objeto.get("citas")),
    )


def _decision(valor: object) -> DecisionGuardada | None:
    objeto = _objeto(valor)
    if objeto is None:
        return None
    return DecisionGuardada(
        motivo=_enumerado(MotivoDeEscritura, objeto.get("motivo")) or MotivoDeEscritura.SIN_CORRUPCION,
        propuesta_del_analisis=_enumerado(CategoriaIncidencia, objeto.get("propuestaDelAnalisis")),
        escalar_a_otrans=_booleano(objeto.get("escalarAOtrans")),
        requiere_revision_humana=_booleano(objeto.get("requiereRevisionHumana")),
        peso_ia=_numero(objeto.get("pesoIa")),
    )


def _modelo(valor: object) -> ModeloGuardado | None:
    objeto = _objeto(valor)
    if objeto is None:
        return None
    return ModeloGuardado(_enumerado(VarianteIa, objeto.get("variante")), _booleano(objeto.get("degradado")))


def _destino_si_titular(valor: object) -> DestinoSiTitular | None:
    objeto = _objeto(valor)
    texto = _texto(objeto.get("texto")) if objeto is not None else None
    if objeto is None or texto is None:
        return None
    return DestinoSiTitular(texto, _texto(objeto.get("entidadDestinoCodigo")))


def _ficha(valor: object) -> FichaDeDerivacion | None:
    objeto = _objeto(valor)
    if objeto is None:
        return None
    codigo = _texto(objeto.get("codigoEntidad"))
    contactos = objeto.get("contactosDisponibles")
    if codigo is None or not isinstance(contactos, list):
        return None
    tipos = [_enumerado(TipoContacto, contacto) for contacto in contactos]
    if None in tipos:
        return None
    return FichaDeDerivacion(
        codigo_entidad=codigo,
        contactos_disponibles=tuple(tipo for tipo in tipos if tipo is not None),
        destino_si_titular=_destino_si_titular(objeto.get("destinoSiTitular")),
        aplica_al_titular=_booleano(objeto.get("aplicaAlTitular")),
    )


def leer_senales_guardadas(crudo: object) -> SenalesGuardadas:
    objeto = _objeto(crudo)
    if objeto is None:
        return SenalesGuardadas()
    return SenalesGuardadas(
        senales=_senales(objeto.get("senales")),
        explicacion=_texto(objeto.get("explicacion")),
        informacion_faltante=_faltantes(objeto.get("informacionFaltante")),
        ficha_derivacion=_ficha(objeto.get("fichaDerivacion")),
        normas=_normas(objeto.get("normas")),
        decision=_decision(objeto.get("decision")),
        modelo=_modelo(objeto.get("modelo")),
    )
