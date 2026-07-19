"""Scraper de InmoUp (inmoup.com.ar) — portal local, API JSON pública.

Su app React consume una API REST en /api/2.0 con auth Basic (credencial
pública embebida en su propio frontend). El buscador es por ruta-slug:
    GET /api/2.0/inmuebles/venta/{grupo}?page=N
La lista de avisos viene en data.pager (24 por página), con campos limpios:
prp_pre_dol (precio USD), prp_pre (precio ARS), sup_cubierta, sup_total,
dormitorios, banos, antiguedad, loc_desc (departamento), prp_dom (dirección),
prp_lat/lng, url_ficha_inmoup.

Bonus: InmoUp trae la ANTIGÜEDAD en el propio listado (no hace falta visitar
fichas). Respetuoso: pausas entre páginas. La primera corrida devuelve un
diagnóstico de calibración."""
from __future__ import annotations

import base64
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any

import httpx

from . import db

log = logging.getLogger("inmoup")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
BASE = "https://inmoup.com.ar/api/2.0/inmuebles/venta"
# Credencial pública (viene en el JS del sitio, se sirve a cualquier visitante).
_AUTH = "Basic " + base64.b64encode(b"developer:Up0358").decode()
PER_PAGE = 24
# grupos de la API → tipo normalizado nuestro.
GRUPOS = {
    "casas": "casa",
    "departamentos": "departamento",
    "lotes-y-terrenos": "terreno",
    "bodegas-y-fincas": "campo",
}


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": UA, "Accept": "application/json",
                                   "Authorization": _AUTH}, timeout=30, follow_redirects=True)


def _num(v: Any) -> float | None:
    """Número tolerante que preserva el signo (las coordenadas son negativas)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", "."))
    return float(m.group()) if m else None


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _parse(it: dict[str, Any], tipo: str, now: str) -> dict[str, Any]:
    lid = it.get("propiedad_id")
    url = it.get("url_ficha_inmoup") or None
    if url and url.startswith("/"):
        url = "https://inmoup.com.ar" + url

    # Precio: preferimos el de dólares (prp_pre_dol); si no hay, pesos (prp_pre).
    usd = _num(it.get("prp_pre_dol"))
    ars = _num(it.get("prp_pre"))
    if usd and usd > 0:
        precio, moneda = usd, "USD"
    elif ars and ars > 0:
        precio, moneda = ars, "ARS"
    else:
        precio, moneda = None, None

    ant = _num(it.get("antiguedad"))
    return {
        "source": "inmoup", "listing_id": str(lid) if lid else None,
        "titulo": (it.get("prp_dom") or it.get("tip_desc") or "Aviso InmoUp")[:200],
        "url": url, "operacion": "venta", "tipo": tipo,
        "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": _num(it.get("sup_cubierta")) or None,
        "m2_total": _num(it.get("sup_total")) or None,
        "ambientes": None,
        "dormitorios": int(it["dormitorios"]) if str(it.get("dormitorios") or "").isdigit() else None,
        "antiguedad": ant if (ant is not None and 0 <= ant <= 150) else None,
        "detail_at": now,  # ya trae antigüedad; no hace falta visitar la ficha
        "provincia": it.get("pro_desc") or "Mendoza",
        "departamento": it.get("loc_desc") or None, "barrio": None,
        "lat": _num(it.get("prp_lat")), "lon": _num(it.get("prp_lng")),
        "fetched_at": now,
    }


def scrape(paginas_por_grupo: int = 8, pausa: float = 3.5) -> dict[str, Any]:
    """Recorre venta de casas/departamentos/terrenos/campos (Mendoza) paginando
    la API y guarda comparables. Devuelve un diagnóstico de calibración."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    diag: dict[str, Any] = {"grupos": [], "muestra": None}

    for slug, tipo in GRUPOS.items():
        vistos: set[str] = set()
        for page in range(1, paginas_por_grupo + 1):
            url = f"{BASE}/{slug}?page={page}"
            try:
                r = _get(url)
                data = r.json().get("data", {})
            except Exception as exc:  # noqa: BLE001
                diag["grupos"].append({"grupo": slug, "pagina": page, "error": str(exc)[:120]})
                break

            items = data.get("pager") or []
            nuevos = 0
            for it in items:
                row = _parse(it, tipo, now)
                lid = row["listing_id"]
                if lid and lid not in vistos:
                    vistos.add(lid)
                    rows.append(row)
                    nuevos += 1

            diag["grupos"].append({"grupo": slug, "pagina": page, "status": r.status_code,
                                   "items": len(items), "nuevos": nuevos, "total": data.get("total")})
            if diag["muestra"] is None and items:
                diag["muestra"] = _parse(items[0], tipo, now)
            if nuevos == 0:
                break
            time.sleep(pausa)

    guardados = db.upsert(rows)
    # La antigüedad no va por upsert (para no pisar la del enriquecimiento diario);
    # como InmoUp la trae en el listado, la persistimos aparte en una sola pasada.
    db.set_details_bulk([(r["source"], r["listing_id"], r["antiguedad"], now)
                         for r in rows if r.get("antiguedad") is not None])
    venta_usd = sum(1 for r in rows if r["precio_usd"])
    con_ant = sum(1 for r in rows if r.get("antiguedad") is not None)
    log.info("Scraper InmoUp: %d guardados (%d en USD, %d con antigüedad).",
             guardados, venta_usd, con_ant)
    return {"guardados": guardados, "venta_usd": venta_usd, "con_antiguedad": con_ant,
            "diagnostico": diag}
