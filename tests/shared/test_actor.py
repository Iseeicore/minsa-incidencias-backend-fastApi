from app.shared.actor import actor_usuario_interno


def test_el_actor_de_un_usuario_interno_lleva_su_correo() -> None:
    assert actor_usuario_interno("ana@minsa.gob.pe") == "usuario:ana@minsa.gob.pe"
