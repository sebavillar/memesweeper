"""Scraper de la web pública de Inmoclick (portal inmobiliario de Mendoza).

Inmoclick renderiza los avisos directamente en el HTML (server-side), con
microdatos schema.org para la dirección (addressLocality = departamento,
addressRegion = provincia). No usa API cerrada ni DataDome, así que se lee con
httpx + BeautifulSoup, igual que MercadoLibre. Fuente muy relevante: es el
portal LOCAL de Mendoza, así que los comparables son híper pertinentes.

Trae solo Mendoza (URLs `...-en-venta-en-mendoza`) y tres tipos: casas,
departamentos y terrenos. Paginado con `?page=N` (24 avisos por página).

⚠️ Va contra los términos de uso del sitio (decisión informada del usuario) y es
frágil: si Inmoclick cambia el HTML, hay que reajustar los selectores.
Respetuoso: poco volumen y pausas entre páginas. La primera corrida devuelve un
diagnóstico para calibrar los selectores si algo cambió."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from . import db

log = logging.getLogger("inmoclick")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
BASE = "https://inmoclick.com/"
PER_PAGE = 24
# Búsquedas por tipo, solo Mendoza. La clave es el tipo normalizado que guardamos.
TIPOS = {
    "casa": "casas-en-venta-en-mendoza",
    "departamento": "departamentos-en-venta-en-mendoza",
    "terreno": "terrenos-en-venta-en-mendoza",
}


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9",
                                   "Accept": "text/html,application/xhtml+xml"},
                     timeout=30, follow_redirects=True)


def _txt(el: Any) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _num(s: str | None) -> int | None:
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def _sup(s: str | None) -> int | None:
    """Superficie tipo '360m2' / '1.234 m²' → 360 / 1234 (corta en la unidad 'm')."""
    t = (s or "").lower().replace("²", "2").split("m")[0]
    return _num(t)


def _parse_card(pd: Any, tipo: str, now: str) -> dict[str, Any]:
    """`pd` es el <div class="property-data"> (la dirección). El precio está en el
    hermano previo (property-image) y las superficies/dormitorios en el hermano
    siguiente (property-tags). Leemos de los hermanos para no cruzar tarjetas."""
    img = pd.find_previous_sibling("div", class_="property-image")
    tags = pd.find_next_sibling("div", class_="property-tags")

    a = pd.select_one("a[href*='/ficha/']") or (img.select_one("a[href*='/ficha/']") if img else None)
    href = (a.get("href") if a else "") or ""
    url = (BASE.rstrip("/") + href) if href.startswith("/") else (href or None)
    # id único: /<inmobiliariaId>-<slug>/inmuebles/<inmuebleId>/ficha/...
    m = re.search(r"/(\d+)-[^/]+/inmuebles/(\d+)/", href)
    listing_id = f"{m.group(1)}-{m.group(2)}" if m else None

    price_el = (img.select_one(".price") if img else None) or pd.find_previous("p", class_="price")
    ptxt = _txt(price_el)
    low = ptxt.lower()
    precio = _num(ptxt)
    if "u$s" in low or "us$" in low or "usd" in low or "dól" in low or "dolar" in low:
        moneda = "USD"
    elif "$" in ptxt:
        moneda = "ARS"
    else:
        moneda = None

    # Ubicación: microdatos schema.org (muy estable), dentro del property-data.
    depto = _txt(pd.select_one("[itemprop='addressLocality']")) or None
    prov = _txt(pd.select_one("[itemprop='addressRegion']")) or None
    calle = _txt(pd.select_one("[itemprop='streetAddress']")) or None
    titulo = ", ".join(x for x in (calle, depto) if x) or _txt(pd.select_one("h4")) or "Aviso Inmoclick"

    sup_tot = _sup(_txt(tags.select_one(".label-sup-total"))) if tags else None
    sup_cub = _sup(_txt(tags.select_one(".label-sup-cub"))) if tags else None
    dorm = _num(_txt(tags.select_one(".label-dormitorio"))) if tags else None

    return {
        "source": "inmoclick", "listing_id": listing_id, "titulo": titulo[:200], "url": url,
        "operacion": "venta", "tipo": tipo, "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": sup_cub, "m2_total": sup_tot, "ambientes": None, "dormitorios": dorm,
        "provincia": prov or "Mendoza", "departamento": depto, "barrio": None,
        "lat": None, "lon": None, "fetched_at": now,
    }


def scrape(paginas_por_tipo: int = 5, pausa: float = 3.5) -> dict[str, Any]:
    """Recorre casas/departamentos/terrenos en venta de Mendoza y guarda comparables.
    Devuelve un diagnóstico (útil para calibrar los selectores si Inmoclick cambia)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    diag: dict[str, Any] = {"paginas": [], "muestra": None}

    for tipo, path in TIPOS.items():
        for page in range(1, paginas_por_tipo + 1):
            url = f"{BASE}{path}?page={page}"
            try:
                r = _get(url)
            except Exception as exc:  # noqa: BLE001
                diag["paginas"].append({"tipo": tipo, "pagina": page, "error": str(exc)[:120]})
                break

            soup = BeautifulSoup(r.text, "lxml")
            # Ancla: cada aviso es un <div class="property-data"> con link a ficha.
            # El precio y las superficies viven en sus divs hermanos (los lee _parse_card).
            cards = [c for c in soup.select("div.property-data")
                     if c.select_one("a[href*='/ficha/']")]

            diag["paginas"].append({"tipo": tipo, "pagina": page, "status": r.status_code,
                                    "tarjetas": len(cards)})

            if not cards:
                if diag["muestra"] is None:
                    diag["muestra"] = {"titulo_pagina": _txt(soup.title), "html_inicio": r.text[:1500]}
                break

            if diag["muestra"] is None:
                cont = cards[0].parent or cards[0]
                diag["muestra"] = {"tarjeta_contenedor": str(cont)[:2400]}

            nuevos = 0
            for c in cards:
                row = _parse_card(c, tipo, now)
                if row["listing_id"]:
                    rows.append(row)
                    nuevos += 1
            if nuevos == 0:  # página sin avisos válidos → no seguir paginando este tipo
                break
            time.sleep(pausa)

    # dedup por listing_id (por las dudas) antes de guardar
    vistos: dict[str, dict[str, Any]] = {}
    for r_ in rows:
        vistos[r_["listing_id"]] = r_
    limpio = list(vistos.values())

    guardados = db.upsert(limpio)
    venta_usd = sum(1 for r in limpio if r["precio_usd"])
    log.info("Scraper Inmoclick: %d guardados (%d en USD).", guardados, venta_usd)
    return {"guardados": guardados, "venta_usd": venta_usd, "diagnostico": diag}
