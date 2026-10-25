from app.shared.pagination import limite_con_extra, pagina_de


def test_con_una_fila_de_mas_hay_siguiente_y_se_recorta_la_pagina() -> None:
    pagina = pagina_de([1, 2, 3], 2, lambda fila: f"cursor-{fila}")

    assert (pagina.items, pagina.siguiente, pagina.hay_mas) == ([1, 2], "cursor-2", True)


def test_sin_fila_de_mas_no_hay_siguiente() -> None:
    pagina = pagina_de([1, 2], 2, lambda fila: f"cursor-{fila}")

    assert (pagina.items, pagina.siguiente, pagina.hay_mas) == ([1, 2], None, False)


def test_una_lista_vacia_da_una_pagina_vacia() -> None:
    pagina = pagina_de(list[int](), 5, str)

    assert (pagina.items, pagina.siguiente, pagina.hay_mas) == ([], None, False)


def test_se_pide_una_fila_de_mas_para_saber_si_hay_siguiente() -> None:
    assert limite_con_extra(50) == 51
