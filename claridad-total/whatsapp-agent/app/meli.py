"""Fetcher de datos de oferta desde la API oficial de MercadoLibre (categoría
Inmuebles MLA1459). Único portal habilitado para uso programático 'sin problema'.

Autenticación: token de app por client_credentials (MELI_CLIENT_ID/SECRET) o un
MELI_ACCESS_TOKEN manual. Guarda los listados normalizados en la base `comparables`."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from . import db
from .config import settings

log = logging.getLogger("meli")
API = "https://api.mercadolibre.com"
CATEGORIA_INMUEBLES = "MLA1459"


def get_token() -> str:
    if settings.meli_access_token:
        return settings.meli_access_token
    if not (settings.meli_client_id and settings.meli_client_secret):
        raise RuntimeError("Faltan credenciales de MercadoLibre (MELI_CLIENT_ID/SECRET o MELI_ACCESS_TOKEN).")
    r = httpx.post(f"{API}/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": settings.meli_client_id,
        "client_secret": settings.meli_client_secret,
    }, headers={"accept": "application/json"}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}


def mendoza_state_id(token: str) -> str:
    r = httpx.get(f"{API}/classified_locations/countries/AR", headers=_headers(token), timeout=20)
    r.raise_for_status()
    for s in r.json().get("states", []):
        if "mendoza" in (s.get("name") or "").lower():
            return s["id"]
    raise RuntimeError("No se encontró el estado 'Mendoza' en las ubicaciones de MELI.")


def _attr(item: dict[str, Any], attr_id: str) -> Any:
    for a in item.get("attributes", []) or []:
        if a.get("id") == attr_id:
            struct = a.get("value_struct") or {}
            return struct.get("number") if struct.get("number") is not None else a.get("value_name")
    return None


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        pass
    s = "".join(ch for ch in str(v) if ch.isdigit() or ch in ".,").replace(".", "").replace(",", ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _tipo(item: dict[str, Any]) -> str | None:
    raw = (_attr(item, "PROPERTY_TYPE") or "").lower()
    if "casa" in raw:
        return "casa"
    if "departamento" in raw or "depto" in raw or "monoambiente" in raw:
        return "departamento"
    return raw or None


def _operacion(item: dict[str, Any]) -> str | None:
    raw = (_attr(item, "OPERATION") or "").lower()
    if "venta" in raw:
        return "venta"
    if "alquiler" in raw:
        return "alquiler"
    return raw or None


def normalize(item: dict[str, Any], now: str) -> dict[str, Any]:
    loc = item.get("location") or {}
    addr = item.get("address") or {}
    moneda = item.get("currency_id")
    precio = item.get("price")
    return {
        "source": "mercadolibre", "listing_id": item.get("id"), "titulo": item.get("title"),
        "url": item.get("permalink"), "operacion": _operacion(item), "tipo": _tipo(item),
        "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": _num(_attr(item, "COVERED_AREA")),
        "m2_total": _num(_attr(item, "TOTAL_AREA")),
        "ambientes": int(_num(_attr(item, "ROOMS")) or 0) or None,
        "dormitorios": int(_num(_attr(item, "BEDROOMS")) or 0) or None,
        "provincia": addr.get("state_name") or (loc.get("state") or {}).get("name"),
        "departamento": addr.get("city_name") or (loc.get("city") or {}).get("name"),
        "barrio": addr.get("neighborhood_name") or (loc.get("neighborhood") or {}).get("name"),
        "lat": loc.get("latitude"), "lon": loc.get("longitude"),
        "fetched_at": now,
    }


def fetch(max_items: int = 200) -> dict[str, Any]:
    """Trae hasta max_items inmuebles de Mendoza y los guarda en la base."""
    token = get_token()
    state = mendoza_state_id(token)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    offset = 0
    while offset < max_items:
        r = httpx.get(f"{API}/sites/MLA/search",
                      params={"category": CATEGORIA_INMUEBLES, "state": state, "limit": 50, "offset": offset},
                      headers=_headers(token), timeout=30)
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            break
        rows.extend(normalize(it, now) for it in results)
        offset += 50
    n = db.upsert(rows)
    venta_usd = sum(1 for r in rows if r["operacion"] == "venta" and r["precio_usd"])
    log.info("MELI Mendoza: %d listados guardados (%d venta en USD).", n, venta_usd)
    return {"guardados": n, "venta_usd": venta_usd}
