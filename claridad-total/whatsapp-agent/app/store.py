"""Persistencia simple en JSON para Fase 0/1: conversaciones, leads y visitas.
En producción esto es PostgreSQL. La interfaz se mantiene igual.

Los datos MUTABLES (conversaciones/leads/visitas) se guardan en DATA_DIR si está
definida (ej. un disco persistente en Render); si no, en la carpeta `data/` del
repo. El inventario NO usa esto: se lee de `data/inventario.json` del repo."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

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
def _sanitize(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """El historial que se manda a la API debe empezar con un mensaje 'user' de
    texto. Al truncar se puede cortar un par tool_use/tool_result y dejar un
    tool_result huérfano al inicio -> error 400. Recortamos desde el frente hasta
    el primer 'user' sin bloques tool_result."""
    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content")
        blocks = content if isinstance(content, list) else []
        if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks):
            return messages[i:]
    return []


def get_conversation(wa_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return _sanitize(_read("_conversations").get(wa_id, []))


def save_conversation(wa_id: str, messages: list[dict[str, Any]]) -> None:
    with _LOCK:
        data = _read("_conversations")
        data[wa_id] = _sanitize(messages[-40:])  # ventana acotada + inicio válido
        _write("_conversations", data)


def _texto(content: Any) -> str:
    """Extrae el texto legible de un `content` (string o bloques Anthropic),
    ignorando bloques tool_use / tool_result."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        partes = [b.get("text", "") for b in content
                  if isinstance(b, dict) and b.get("type") == "text"]
        return " ".join(p for p in partes if p).strip()
    return ""


def transcript(wa_id: str) -> list[dict[str, str]]:
    """Conversación legible (solo texto user/assistant) para mostrar en el panel."""
    with _LOCK:
        msgs = _read("_conversations").get(wa_id, [])
    out: list[dict[str, str]] = []
    for m in msgs:
        if m.get("role") not in ("user", "assistant"):
            continue
        txt = _texto(m.get("content"))
        if txt:
            out.append({"role": m["role"], "text": txt})
    return out


def last_message(wa_id: str) -> dict[str, str] | None:
    t = transcript(wa_id)
    return t[-1] if t else None


# ---- Leads ----
def upsert_lead(wa_id: str, campos: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        data = _read("_leads")
        nuevo = wa_id not in data
        lead = data.get(wa_id, {"wa_id": wa_id})
        lead.update({k: v for k, v in campos.items() if v is not None})
        if nuevo:
            lead.setdefault("creado", _now())
        lead["actualizado"] = _now()
        data[wa_id] = lead
        _write("_leads", data)
        return lead


def touch_lead(wa_id: str) -> None:
    """Marca actividad de un lead aunque no cambien sus datos (cada mensaje que
    entra). Crea el lead mínimo si es la primera vez que escribe este número."""
    with _LOCK:
        data = _read("_leads")
        lead = data.get(wa_id, {"wa_id": wa_id, "creado": _now()})
        lead["actualizado"] = _now()
        lead["mensajes"] = int(lead.get("mensajes", 0)) + 1
        data[wa_id] = lead
        _write("_leads", data)


def list_leads() -> list[dict[str, Any]]:
    with _LOCK:
        return list(_read("_leads").values())


# ---- Visitas ----
def add_visita(visita: dict[str, Any]) -> None:
    with _LOCK:
        data = _read("_visitas")
        visita.setdefault("creada", _now())
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
