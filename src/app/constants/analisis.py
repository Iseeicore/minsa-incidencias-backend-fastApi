from app.enums.informacion_faltante_ia import InformacionFaltanteIa

REQUISITO_POR_INFORMACION_FALTANTE: dict[InformacionFaltanteIa, str] = {
    InformacionFaltanteIa.HECHO_DETALLADO: "AM-REQ-HECHO-DETALLADO",
    InformacionFaltanteIa.AUTOR_O_CARGO: "AM-REQ-AUTORES",
    InformacionFaltanteIa.ENTIDAD_O_UNIDAD: "AM-REQ-ENTIDAD",
    InformacionFaltanteIa.PRUEBAS: "AM-REQ-PRUEBAS",
}
