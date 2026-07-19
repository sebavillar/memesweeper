"""Scraper de MendozaProp (mendozaprop.com) — portal local, API JSON pública.

Su web (Next.js) pide los avisos a un endpoint interno abierto:
    GET /api/properties?operationType=2&page=N   (operationType 2 = venta)
que devuelve una lista de avisos con campos limpios (price, currency_id,
m2/m2_covered, bedrooms, property_type_name, address, regions, images).

Sin autenticación ni escudos. Paginamos hasta que no aparezcan avisos nuevos.
Respetuoso: pausas entre páginas. La primera corrida devuelve un diagnóstico
para calibrar si algo cambió."""
from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any

import httpx

from . import db

log = logging.getLogger("mendozaprop")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
API = "https://www.mendozaprop.com/api/properties"
OP_VENTA = 2  # operationType: 1 = alquiler, 2 = venta
# currency_id del portal: 1 = USD (dólar), 2 = ARS (peso).
_MONEDA = {1: "USD", 2: "ARS"}


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": UA, "Accept": "application/json"},
                     timeout=30, follow_redirects=True)


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    d = re.sub(r"[^\d.]", "", str(v).replace(",", "."))
    try:
        return float(d) if d else None
    except ValueError:
        return None


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _slug(s: str) -> str:
    s = _norm(s)
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def _tipo(nombre: str) -> str | None:
    v = _norm(nombre)
    if not v:
        return None
    if "casa" in v or "chalet" in v or "duplex" in v:
        return "casa"
    if "departamento" in v or "depto" in v or v == "ph" or "monoambiente" in v or "loft" in v:
        return "departamento"
    if "terreno" in v or "lote" in v:
        return "terreno"
    if "campo" in v or "finca" in v or "chacra" in v or "quinta" in v:
        return "campo"
    return v  # local, oficina, galpon, etc.


def _regiones(it: dict[str, Any]) -> tuple[str | None, str | None]:
    """Devuelve (departamento, barrio) a partir de `regions` (forma variable) +
    `address`. La normalización final a departamento de Mendoza la hace la API."""
    reg = it.get("regions")
    nombres: list[str] = []
    if isinstance(reg, list):
        for x in reg:
            if isinstance(x, dict):
                nombres.append(str(x.get("name") or x.get("nombre") or ""))
            elif isinstance(x, str):
                nombres.append(x)
    elif isinstance(reg, str):
        nombres = [p.strip() for p in reg.split(",")]
    elif isinstance(reg, dict):
        nombres = [str(reg.get("name") or reg.get("nombre") or "")]
    nombres = [n for n in nombres if n]
    depto = nombres[-1] if nombres else None
    barrio = nombres[0] if len(nombres) >= 2 else (it.get("address") or None)
    return depto, barrio


def _parse(it: dict[str, Any], now: str) -> dict[str, Any]:
    lid = it.get("id")
    titulo = it.get("title") or "Aviso MendozaProp"
    url = f"https://www.mendozaprop.com/{_slug(titulo)}/{lid}" if lid else None

    precio = _num(it.get("price"))
    moneda = _MONEDA.get(it.get("currency_id"))
    tipo = _tipo(str(it.get("property_type_name") or ""))
    depto, barrio = _regiones(it)

    m2_cub = _num(it.get("m2_covered"))
    m2_tot = _num(it.get("m2"))
    dorm = int(it["bedrooms"]) if str(it.get("bedrooms") or "").isdigit() else None
    amb = int(it["rooms"]) if str(it.get("rooms") or "").isdigit() else None

    return {
        "source": "mendozaprop", "listing_id": str(lid) if lid else None,
        "titulo": str(titulo)[:200], "url": url, "operacion": "venta", "tipo": tipo,
        "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": m2_cub or None, "m2_total": m2_tot or None,
        "ambientes": amb, "dormitorios": dorm,
        "provincia": "Mendoza", "departamento": depto, "barrio": barrio,
        "lat": None, "lon": None, "fetched_at": now,
    }


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in ("data", "properties", "results", "items"):
            v = payload.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def scrape(max_pages: int = 25, pausa: float = 3.5) -> dict[str, Any]:
    """Pagina la oferta en venta de MendozaProp y guarda comparables. Corta cuando
    una página no trae avisos nuevos (id ya visto), así se banca que `page` no
    exista sin caer en loop. Devuelve un diagnóstico de calibración."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    vistos: set[str] = set()
    diag: dict[str, Any] = {"paginas": [], "muestra": None}

    for page in range(1, max_pages + 1):
        url = f"{API}?operationType={OP_VENTA}&page={page}"
        try:
            r = _get(url)
        except Exception as exc:  # noqa: BLE001
            diag["paginas"].append({"pagina": page, "error": str(exc)[:120]})
            break

        try:
            items = _items(r.json())
        except Exception:  # noqa: BLE001
            diag["paginas"].append({"pagina": page, "status": r.status_code, "error": "no-JSON"})
            break

        nuevos = 0
        for it in items:
            row = _parse(it, now)
            lid = row["listing_id"]
            if lid and lid not in vistos:
                vistos.add(lid)
                rows.append(row)
                nuevos += 1

        diag["paginas"].append({"pagina": page, "status": r.status_code,
                                "items": len(items), "nuevos": nuevos})
        if diag["muestra"] is None and items:
            it0 = items[0]
            diag["muestra"] = {"transaction_type_name": it0.get("transaction_type_name"),
                               "parseado": _parse(it0, now)}
        if nuevos == 0:  # página vacía o repetida → no hay más
            break
        time.sleep(pausa)

    guardados = db.upsert(rows)
    venta_usd = sum(1 for r in rows if r["precio_usd"])
    log.info("Scraper MendozaProp: %d guardados (%d en USD).", guardados, venta_usd)
    return {"guardados": guardados, "venta_usd": venta_usd, "diagnostico": diag}
