from app.filtro_corrupcion.domain.cola_de_clasificacion import CasoPendiente, FilaAlarma


def test_el_caso_pendiente_guarda_el_establecimiento_opcional() -> None:
    sin_establecimiento = CasoPendiente("id-1", "MINSA-2026-000001", "relato", None)

    assert (sin_establecimiento.codigo, sin_establecimiento.establecimiento) == ("MINSA-2026-000001", None)


def test_la_fila_de_alarma_guarda_los_codigos_atrasados() -> None:
    fila = FilaAlarma(2, 61.5, ("MINSA-2026-000001", "MINSA-2026-000002"))

    assert (fila.atrasados, fila.minutos, len(fila.codigos)) == (2, 61.5, 2)
