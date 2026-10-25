class ClaseDeLexicoDesconocida(ValueError):
    def __init__(self, elemento: str) -> None:
        super().__init__(f"La clase de léxico {elemento} no existe.")
