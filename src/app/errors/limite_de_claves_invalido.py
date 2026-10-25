class LimiteDeClavesInvalido(ValueError):
    def __init__(self, valor: object) -> None:
        super().__init__(f"max_keys debe ser un entero positivo, recibido {valor!r}")
