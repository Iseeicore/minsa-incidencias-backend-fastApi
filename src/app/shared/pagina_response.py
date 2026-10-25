from app.shared.api_model import ApiModel


class PaginaResponse[T](ApiModel):
    items: list[T]
    siguiente: str | None
    hay_mas: bool
