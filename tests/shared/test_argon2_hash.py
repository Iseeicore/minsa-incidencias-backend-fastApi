import pytest

from app.shared.argon2_hash import canonical_argon2_hash

SAL = "c29tZXNhbHQ"
CLAVE = "aGFzaA"


def test_un_hash_con_los_parametros_en_otro_orden_se_reordena() -> None:
    entrada = f"$argon2id$v=19$m=65536,p=4,t=3${SAL}${CLAVE}"

    assert canonical_argon2_hash(entrada) == f"$argon2id$v=19$m=65536,t=3,p=4${SAL}${CLAVE}"


def test_un_hash_ya_canonico_no_cambia() -> None:
    canonico = f"$argon2id$v=19$m=65536,t=3,p=4${SAL}${CLAVE}"

    assert canonical_argon2_hash(canonico) == canonico


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "no-es-un-hash",
        "$argon2id$v=19",
        "$argon2id$v=19$m=1,t=2$s$h",
        "$argon2id$v=19$m=1,t=2,x=3$s$h",
        "$argon2id$v=19$a,b,c$s$h",
    ],
)
def test_lo_que_no_tiene_la_forma_esperada_queda_igual(entrada: str) -> None:
    assert canonical_argon2_hash(entrada) == entrada
