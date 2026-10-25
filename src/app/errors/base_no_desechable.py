from app.constants.database import SUFIJOS_DE_BASE_DESECHABLE


class BaseNoDesechable(ValueError):
    def __init__(self) -> None:
        sufijos = ", ".join(SUFIJOS_DE_BASE_DESECHABLE)
        super().__init__(f"Este comando solo corre contra una base desechable: su nombre debe terminar en {sufijos}.")
