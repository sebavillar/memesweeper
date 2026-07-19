"""Scraper de la web pública de MercadoLibre (inmuebles en venta, Mendoza).

La API de búsqueda de MELI está cerrada (PolicyAgent 403), así que leemos las
páginas públicas de resultados. Uso: interno de la inmobiliaria para armar
comparables de mercado. Respetuoso: poco volumen, pausas entre páginas.

⚠️ Va contra los términos de uso del sitio (decisión informada del usuario) y es
frágil: si MELI cambia el HTML, hay que reajustar los selectores. La primera
corrida es de CALIBRACIÓN: devuelve un diagnóstico para afinar los selectores."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from . import db

log = logging.getLogger("scraper")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
BASE = "https://inmuebles.mercadolibre.com.ar/venta/mendoza/"
PER_PAGE = 48
CARD_SELECTORS = [
    "li.ui-search-layout__item", "div.ui-search-result__wrapper",
    "div.poly-card", "div.andes-card.poly-card", "li.ui-search-layout__item div.andes-card",
]


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9",
                                   "Accept": "text/html,application/xhtml+xml"},
                     timeout=30, follow_redirects=True)


def _txt(el: Any) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _int(s: str | None) -> int | None:
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def _parse_card(card: Any, now: str) -> dict[str, Any]:
    a = card.select_one("a[href*='/MLA-'], a.ui-search-link, a.poly-component__title")
    href = (a.get("href") if a else "") or ""
    url = href.split("#")[0] or None
    m = re.search(r"MLA-?(\d+)", href)
    listing_id = "MLA" + m.group(1) if m else None

    titulo = _txt(a) or _txt(card.select_one("h2, .poly-component__title, .ui-search-item__title"))
    precio = _int(_txt(card.select_one(".andes-money-amount__fraction, .price-tag-fraction")))

    blob = _txt(card)
    low = blob.lower()
    moneda = "USD" if ("u$s" in low or "usd" in low) else ("ARS" if "$" in blob else None)

    m2 = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*m²", blob))
    amb = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*ambiente", low))
    dorm = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*dormitor", low))
    loc = _txt(card.select_one(".ui-search-item__location, .poly-component__location, "
                               ".ui-search-item__group__element--location"))

    tl = (titulo or "").lower()
    tipo = "casa" if "casa" in tl else \
        "departamento" if ("departamento" in tl or "depto" in tl or "monoambiente" in tl) else None

    return {
        "source": "mercadolibre", "listing_id": listing_id, "titulo": titulo, "url": url,
        "operacion": "venta", "tipo": tipo, "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": m2, "m2_total": None, "ambientes": amb, "dormitorios": dorm,
        "provincia": "Mendoza", "departamento": loc or None, "barrio": None,
        "lat": None, "lon": None, "fetched_at": now,
    }


def scrape(max_pages: int = 6, pausa: float = 3.0) -> dict[str, Any]:
    """Recorre páginas de resultados y guarda comparables. Devuelve un diagnóstico
    (útil para calibrar los selectores en la primera corrida)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    diag: dict[str, Any] = {"paginas": [], "muestra": None}

    for page in range(max_pages):
        offset = page * PER_PAGE
        url = BASE if page == 0 else f"{BASE}_Desde_{offset + 1}_NoIndex_True"
        try:
            r = _get(url)
        except Exception as exc:  # noqa: BLE001
            diag["paginas"].append({"url": url, "error": str(exc)[:120]})
            break

        soup = BeautifulSoup(r.text, "lxml")
        cards: list[Any] = []
        sel_ok = None
        for sel in CARD_SELECTORS:
            cards = soup.select(sel)
            if cards:
                sel_ok = sel
                break

        diag["paginas"].append({"pagina": page + 1, "status": r.status_code,
                                "bytes": len(r.text), "tarjetas": len(cards), "selector": sel_ok})

        if not cards:
            if diag["muestra"] is None:
                diag["muestra"] = {"titulo_pagina": _txt(soup.title), "html_inicio": r.text[:1600]}
            break

        if diag["muestra"] is None:
            diag["muestra"] = {"primera_tarjeta": str(cards[0])[:2200]}

        for c in cards:
            row = _parse_card(c, now)
            if row["listing_id"]:
                rows.append(row)
        time.sleep(pausa)

    guardados = db.upsert(rows)
    venta_usd = sum(1 for r in rows if r["precio_usd"])
    log.info("Scraper MELI web: %d guardados (%d en USD).", guardados, venta_usd)
    return {"guardados": guardados, "venta_usd": venta_usd, "diagnostico": diag}
