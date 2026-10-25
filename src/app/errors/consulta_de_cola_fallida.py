class ConsultaDeColaFallida(RuntimeError):
    def __init__(self) -> None:
        super().__init__("No se pudo consultar la cola de incidencias por clasificar.")
