import json

import pytest

from app.shared.password_hasher import Argon2PasswordHasher
from tests.helpers.base import HASHES_DEL_NODO

HASHES = json.loads(HASHES_DEL_NODO.read_text(encoding="utf-8"))


@pytest.mark.parametrize("vector", HASHES, ids=["ascii", "unicode", "larga"])
async def test_verifica_los_hashes_argon2id_generados_por_el_node(vector: dict[str, str]) -> None:
    assert await Argon2PasswordHasher().verify(vector["hash"], vector["clave"]) is True


async def test_rechaza_una_clave_distinta_de_la_del_hash_del_node() -> None:
    assert await Argon2PasswordHasher().verify(HASHES[0]["hash"], "otra-clave") is False


@pytest.mark.parametrize("huella", ["", "no-es-un-hash", "$argon2id$v=19$m=1$roto"])
async def test_un_hash_ilegible_no_verifica_en_vez_de_fallar(huella: str) -> None:
    assert await Argon2PasswordHasher().verify(huella, "clave") is False


async def test_el_hash_propio_usa_los_mismos_parametros_que_el_node_y_se_verifica() -> None:
    hasher = Argon2PasswordHasher()

    huella = await hasher.hash("clave-nueva")

    assert huella.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert HASHES[0]["hash"].startswith("$argon2id$v=19$m=65536,p=4,t=3$")
    assert await hasher.verify(huella, "clave-nueva") is True
    assert await hasher.verify(huella, "clave-vieja") is False
