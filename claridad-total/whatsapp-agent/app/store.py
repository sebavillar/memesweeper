"""Persistencia simple en JSON para Fase 0/1: conversaciones, leads y visitas.
En producción esto es PostgreSQL. La interfaz se mantiene igual.

Los datos MUTABLES (conversaciones/leads/visitas) se guardan en DATA_DIR si está
definida (ej. un disco persistente en Render); si no, en la carpeta `data/` del
repo. El inventario NO usa esto: se lee de `data/inventario.json` del repo."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

_DATA_DIR = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent / "data"))
_LOCK = threading.Lock()


def _path(name: str) -> Path:
    return _DATA_DIR / f"{name}.json"


def _read(name: str) -> dict[str, Any]:
    p = _path(name)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _write(name: str, data: dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# ---- Conversaciones (historial de mensajes por número) ----
def get_conversation(wa_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return _read("_conversations").get(wa_id, [])


def save_conversation(wa_id: str, messages: list[dict[str, Any]]) -> None:
    with _LOCK:
        data = _read("_conversations")
        data[wa_id] = messages[-40:]  # ventana de contexto acotada
        _write("_conversations", data)


# ---- Leads ----
def upsert_lead(wa_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        data = _read("_leads")
        lead = data.get(wa_id, {"wa_id": wa_id})
        lead.update({k: v for k, v in campos.items() if v is not None})
        data[wa_id] = lead
        _write("_leads", data)
        return lead


def list_leads() -> list[dict[str, Any]]:
    with _LOCK:
        return list(_read("_leads").values())


# ---- Visitas ----
def add_visita(visita: dict[str, Any]) -> None:
    with _LOCK:
        data = _read("_visitas")
        data.setdefault("visitas", []).append(visita)
        _write("_visitas", data)


def list_visitas() -> list[dict[str, Any]]:
    with _LOCK:
        return _read("_visitas").get("visitas", [])


# ---- Estadísticas por inmueble ----
def bump_prop_stat(prop_id: str, metric: str, n: int = 1) -> None:
    """Suma a un contador por propiedad (ofrecida, ficha, consultas, visitas)."""
    if not prop_id:
        return
    with _LOCK:
        data = _read("_prop_stats")
        st = data.setdefault(prop_id, {})
        st[metric] = st.get(metric, 0) + n
        _write("_prop_stats", data)


def get_prop_stats(prop_id: str) -> dict[str, Any]:
    with _LOCK:
        return _read("_prop_stats").get(prop_id, {})


def all_prop_stats() -> dict[str, Any]:
    with _LOCK:
        return _read("_prop_stats")
