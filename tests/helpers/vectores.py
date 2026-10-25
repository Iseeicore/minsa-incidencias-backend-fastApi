import json
from pathlib import Path
from typing import Any

VECTORES_DEL_NODO = Path(__file__).parents[1] / "fixtures" / "vectores_node.json"


def vectores_del_nodo() -> dict[str, Any]:
    vectores: dict[str, Any] = json.loads(VECTORES_DEL_NODO.read_text(encoding="utf-8"))
    return vectores
