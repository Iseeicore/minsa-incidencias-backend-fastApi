class ConexionPerdida(Exception):
    def __init__(self) -> None:
        super().__init__("Se cerró la conexión de escucha de PostgreSQL.")
