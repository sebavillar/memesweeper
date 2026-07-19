"""Scraper de la oferta pública de RE/MAX Argentina (inmuebles en venta, Mendoza).

El sitio de RE/MAX (remax.com.ar) arma los avisos en el navegador consultando una
API JSON interna (tipo `.../listings/findAll?...`). No se puede descubrir esa URL
desde acá (el proxy bloquea el dominio), así que la dejamos CONFIGURABLE:

    REMAX_API_URL="https://<host>/.../findAll?..."   (en el .env del server)

Cómo obtenerla (una sola vez, 2 min): abrí remax.com.ar, filtrá "Comprar · Mendoza",
DevTools (F12) → pestaña **Network** → filtro **Fetch/XHR** → recargá. Buscá la
llamada que devuelve JSON con los avisos (suele decir `findAll` o `listings`).
Botón derecho → *Copy → Copy URL*. Pegala en REMAX_API_URL.

Respetuoso: poco volumen, pausas entre páginas. La primera corrida es de
CALIBRACIÓN: devuelve el primer item crudo para mapear los campos con precisión.

⚠️ Va contra los términos de uso del sitio (decisión informada del usuario) y es
frágil: si RE/MAX cambia la API, hay que reajustar el mapeo/paginado."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from . import db
from .config import settings

log = logging.getLogger("remax")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
PER_PAGE = 50


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={
        "User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9",
        "Accept": "application/json, text/plain, */*",
    }, timeout=30, follow_redirects=True)


def _first(d: dict[str, Any], *keys: str) -> Any:
    """Devuelve el primer valor no-nulo de una lista de claves posibles."""
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None


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


def _int(v: Any) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def _items(payload: Any) -> list[dict[str, Any]]:
    """Extrae la lista de avisos del JSON, tolerando distintas envolturas."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "results", "items", "listings", "content", "docs", "rows"):
            v = payload.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
            if isinstance(v, dict):  # p. ej. {"data": {"results": [...]}}
                inner = _items(v)
                if inner:
                    return inner
    return []


def _dig(d: dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


def _tipo_from(valor: str) -> str | None:
    """Normaliza el `type.value` de RE/MAX a nuestras categorías.
    Valores vistos: casa, departamento, terrenos_y_lotes, campo, hotel,
    edificio, oficina, fondo_de_comercio, local, ph, ..."""
    v = _norm(valor)
    if not v:
        return None
    if "casa" in v or "chalet" in v or "duplex" in v:
        return "casa"
    if "departamento" in v or "depto" in v or v == "ph" or "monoambiente" in v or "loft" in v:
        return "departamento"
    if "terreno" in v or "lote" in v:  # 'terrenos_y_lotes'
        return "terreno"
    if "campo" in v or "finca" in v or "chacra" in v or "quinta" in v:
        return "campo"
    return v  # hotel, edificio, oficina, local, etc. (se guardan pero no matchean inventario)


def _zona_from(address_info: str) -> tuple[str, str | None, str | None]:
    """`addressInfo` = 'Barrio, Departamento, Provincia' → (provincia, depto, barrio)."""
    parts = [p.strip() for p in (address_info or "").split(",") if p.strip()]
    prov = parts[-1] if parts else "Mendoza"
    depto = parts[-2] if len(parts) >= 2 else None
    barrio = parts[0] if len(parts) >= 3 else None
    return prov, depto, barrio


def _parse_item(it: dict[str, Any], now: str) -> dict[str, Any]:
    lid = _first(it, "id", "_id", "listingId", "internalId")
    slug = it.get("slug")
    if slug:
        url = str(slug) if str(slug).startswith("http") else f"https://www.remax.com.ar/listings/{slug}"
    else:
        url = f"https://www.remax.com.ar/listings/{lid}" if lid else None

    titulo = _first(it, "title", "displayAddress") or "Publicación RE/MAX"

    precio = _num(it.get("price"))
    moneda_v = _norm(str(_dig(it, "currency", "value") or ""))
    moneda = "USD" if ("usd" in moneda_v or "dolar" in moneda_v) else \
             ("ARS" if ("ars" in moneda_v or "peso" in moneda_v) else None)

    tipo = _tipo_from(str(_dig(it, "type", "value") or ""))

    op = _norm(str(_dig(it, "operation", "value") or ""))
    operacion = "alquiler" if op in ("rent", "alquiler") else "venta"

    # dimensionCovered = m² cubiertos (construidos); dimensionLand = m² de terreno.
    m2_cub = _num(it.get("dimensionCovered"))
    m2_tot = _num(it.get("dimensionLand")) or _num(it.get("dimensionTotalBuilt"))
    amb = _int(it.get("totalRooms"))
    dorm = _int(it.get("bedrooms"))

    prov, depto, barrio = _zona_from(str(it.get("addressInfo") or ""))

    lat = lon = None
    coords = _dig(it, "location", "coordinates")  # GeoJSON: [lon, lat]
    if isinstance(coords, list) and len(coords) == 2:
        lon, lat = _num(coords[0]), _num(coords[1])

    return {
        "source": "remax", "listing_id": str(lid) if lid else None,
        "titulo": str(titulo)[:200], "url": url, "operacion": operacion, "tipo": tipo,
        "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": m2_cub or None, "m2_total": m2_tot or None,
        "ambientes": amb or None, "dormitorios": dorm,
        "provincia": prov or "Mendoza", "departamento": depto, "barrio": barrio,
        "lat": lat, "lon": lon, "fetched_at": now,
    }


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _page_url(base: str, page: int) -> str:
    """Ajusta el parámetro de página/offset del URL base (best-effort)."""
    if page == 0:
        return base
    offset = page * PER_PAGE
    sep = "&" if "?" in base else "?"
    # Si el URL ya trae pageSize/page, respetamos; si no, agregamos page.
    if re.search(r"[?&]page=", base):
        return re.sub(r"([?&]page=)\d+", lambda m: f"{m.group(1)}{page}", base)
    if re.search(r"[?&]offset=", base):
        return re.sub(r"([?&]offset=)\d+", lambda m: f"{m.group(1)}{offset}", base)
    return f"{base}{sep}page={page}"


def scrape(max_pages: int = 4, pausa: float = 4.0) -> dict[str, Any]:
    """Recorre la API JSON de RE/MAX y guarda comparables. Devuelve un diagnóstico
    (útil para calibrar el mapeo de campos en la primera corrida)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    diag: dict[str, Any] = {"paginas": [], "muestra_item": None}

    base = (settings.remax_api_url or "").strip()
    if not base:
        msg = ("falta REMAX_API_URL: obtené la URL de la API JSON desde DevTools "
               "(Network → Fetch/XHR) y ponela en el .env. Ver app/remax.py.")
        log.warning("Scraper RE/MAX: %s", msg)
        return {"guardados": 0, "venta_usd": 0, "error": msg, "diagnostico": diag}

    rows: list[dict[str, Any]] = []
    for page in range(max_pages):
        url = _page_url(base, page)
        try:
            r = _get(url)
        except Exception as exc:  # noqa: BLE001
            diag["paginas"].append({"url": url[:160], "error": str(exc)[:120]})
            break

        info: dict[str, Any] = {"pagina": page + 1, "status": r.status_code, "bytes": len(r.text)}
        try:
            payload = r.json()
        except Exception:  # noqa: BLE001
            info["error"] = "respuesta no-JSON"
            info["cuerpo_inicio"] = r.text[:400]
            diag["paginas"].append(info)
            break

        items = _items(payload)
        info["items"] = len(items)
        diag["paginas"].append(info)
        if not items:
            if diag["muestra_item"] is None:
                diag["muestra_item"] = {"nota": "sin items; claves del JSON",
                                        "claves": list(payload.keys())[:20]
                                        if isinstance(payload, dict) else "lista/otro"}
            break

        if diag["muestra_item"] is None:
            diag["muestra_item"] = items[0]  # item crudo: sirve para mapear campos

        for it in items:
            row = _parse_item(it, now)
            if row["listing_id"]:
                rows.append(row)
        time.sleep(pausa)

    guardados = db.upsert(rows)
    venta_usd = sum(1 for r in rows if r["precio_usd"])
    log.info("Scraper RE/MAX: %d guardados (%d en USD).", guardados, venta_usd)
    return {"guardados": guardados, "venta_usd": venta_usd, "diagnostico": diag}
