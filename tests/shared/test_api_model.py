from app.shared.api_model import ApiModel


class Ejemplo(ApiModel):
    nombre_completo: str
    hay_mas: bool


def test_el_modelo_serializa_en_camel_case_y_acepta_ambos_nombres() -> None:
    desde_camel = Ejemplo.model_validate({"nombreCompleto": "Ana", "hayMas": True})
    desde_snake = Ejemplo(nombre_completo="Ana", hay_mas=True)

    assert desde_camel == desde_snake
    assert desde_snake.model_dump(by_alias=True) == {"nombreCompleto": "Ana", "hayMas": True}
