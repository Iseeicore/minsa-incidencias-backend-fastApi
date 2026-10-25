import pytest

from app.filtro_corrupcion.domain.nombres_propios import nombres_propios_de


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Me atendio Carlos Perez ayer", ["Carlos Perez"]),
        ("Maria Lopez Rojas y Juan Torres", ["Maria Lopez Rojas", "Juan Torres"]),
        ("Se llama Ñandú Pérez", ["Ñandú Pérez"]),
        ("Hablo con Carlos", []),
        ("sin nombres propios aqui", []),
        ("Carlos  \n  Perez", ["Carlos  \n  Perez"]),
        ("CARLOS PEREZ", []),
        ("McDonald Perez", ["Donald Perez"]),
        ("Carlos Perez.Ana Torres", ["Carlos Perez", "Ana Torres"]),
        ("Carlos Perez, Ana Torres", ["Carlos Perez", "Ana Torres"]),
        ("Ab Cd Ef", ["Ab Cd Ef"]),
        ("A B", []),
        ("", []),
        ("Carlos\u00a0Perez", ["Carlos\u00a0Perez"]),
    ],
)
def test_encuentra_secuencias_de_palabras_con_mayuscula_inicial_y_minusculas(texto: str, esperado: list[str]) -> None:
    assert nombres_propios_de(texto) == esperado
