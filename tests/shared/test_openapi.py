from fastapi import FastAPI

from app.shared.openapi import drop_default_validation_response


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/uno")
    async def uno(cantidad: int) -> dict[str, int]:
        return {"cantidad": cantidad}

    return app


def test_sin_la_limpieza_fastapi_documenta_el_422_por_defecto() -> None:
    especificacion = _app().openapi()

    assert "422" in especificacion["paths"]["/uno"]["get"]["responses"]
    assert "HTTPValidationError" in especificacion["components"]["schemas"]


def test_la_limpieza_quita_el_422_por_defecto_y_sus_esquemas() -> None:
    app = _app()
    drop_default_validation_response(app)

    especificacion = app.openapi()

    assert "422" not in especificacion["paths"]["/uno"]["get"]["responses"]
    assert "HTTPValidationError" not in especificacion.get("components", {}).get("schemas", {})
    assert app.openapi() is especificacion


def test_un_422_propio_se_conserva() -> None:
    app = FastAPI()

    @app.get("/dos", responses={422: {"description": "Regla de negocio"}})
    async def dos() -> dict[str, int]:
        return {}

    drop_default_validation_response(app)

    assert "422" in app.openapi()["paths"]["/dos"]["get"]["responses"]
