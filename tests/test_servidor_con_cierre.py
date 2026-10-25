import signal

import uvicorn
from fastapi import FastAPI

from app.__main__ import ServidorConCierreDeEventos


def test_al_recibir_la_senal_de_apagado_cierra_los_flujos_antes_de_que_el_servidor_espere_a_los_clientes() -> None:
    orden: list[str] = []
    servidor = ServidorConCierreDeEventos(uvicorn.Config(FastAPI()), lambda: orden.append("flujos cerrados"))

    servidor.handle_exit(signal.SIGTERM, None)
    orden.append(f"debe salir: {servidor.should_exit}")

    assert orden == ["flujos cerrados", "debe salir: True"]
