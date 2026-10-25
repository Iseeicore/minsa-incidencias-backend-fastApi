from typing import TYPE_CHECKING, Any

from app.constants.http import DEFAULT_VALIDATION_SCHEMAS, DEFAULT_VALIDATION_STATUS

if TYPE_CHECKING:
    from fastapi import FastAPI


def drop_default_validation_response(app: FastAPI) -> None:
    original = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = original()
        for item in schema.get("paths", {}).values():
            for operation in item.values():
                if _is_default(operation):
                    operation["responses"].pop(DEFAULT_VALIDATION_STATUS)
        for name in DEFAULT_VALIDATION_SCHEMAS:
            schema.get("components", {}).get("schemas", {}).pop(name, None)
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


def _is_default(operation: dict[str, Any]) -> bool:
    response = operation.get("responses", {}).get(DEFAULT_VALIDATION_STATUS, {})
    reference = response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
    return bool(reference.endswith("HTTPValidationError"))
