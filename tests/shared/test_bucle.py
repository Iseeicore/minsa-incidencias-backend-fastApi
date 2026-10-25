from app.shared.bucle import ejecutar_corutina


async def _suma(a: int, b: int) -> int:
    return a + b


def test_ejecuta_la_corutina_en_un_bucle_nuevo_y_devuelve_su_resultado() -> None:
    assert ejecutar_corutina(_suma(2, 3)) == 5
