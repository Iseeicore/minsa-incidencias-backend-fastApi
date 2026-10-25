class AlcanceDeIncidenciaInvalido(ValueError):
    def __init__(self) -> None:
        super().__init__("El aviso de cambio no trae un alcance de incidencia válido.")
