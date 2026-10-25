class ParametrosSql:
    def __init__(self) -> None:
        self._valores: dict[str, object] = {}

    def agregar(self, valor: object) -> str:
        nombre = f"p{len(self._valores)}"
        self._valores[nombre] = valor
        return f":{nombre}"

    def con_tipo(self, valor: object, tipo: str) -> str:
        return f"CAST({self.agregar(valor)} AS {tipo})"

    @property
    def valores(self) -> dict[str, object]:
        return self._valores
