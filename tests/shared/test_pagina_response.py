from app.shared.pagina_response import PaginaResponse


def test_la_pagina_se_serializa_con_los_nombres_del_contrato() -> None:
    pagina = PaginaResponse[int](items=[1, 2], siguiente=None, hay_mas=False)

    assert pagina.model_dump(by_alias=True) == {"items": [1, 2], "siguiente": None, "hayMas": False}
