class RegistroEnMemoria:
    def __init__(self) -> None:
        self.eventos: list[tuple[str, str, dict[str, object]]] = []

    def info(self, evento: str, **datos: object) -> None:
        self.eventos.append(("info", evento, datos))

    def warning(self, evento: str, **datos: object) -> None:
        self.eventos.append(("warning", evento, datos))

    def error(self, evento: str, **datos: object) -> None:
        self.eventos.append(("error", evento, datos))
