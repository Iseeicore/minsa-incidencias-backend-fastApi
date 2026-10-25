from app.shared.sin_sesiones import SinSesiones


async def test_ninguna_sesion_se_resuelve() -> None:
    assert await SinSesiones().resolve("0b9f8c9e-7d0a-4f5b-9a3c-1e2d3c4b5a69") is None
