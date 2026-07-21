"""Parser de Argenprop (HTML server-rendered) — venta en Mendoza.

Argenprop bloquea las IPs de datacenter (CloudFront responde 403 a servidores),
pero SÍ deja pasar IPs residenciales. Por eso el HTML lo baja el usuario desde su
casa y lo sube crudo al servidor (POST /api/v1/ingest); acá SOLO lo parseamos.

Frágil como todo scraping de HTML: si Argenprop cambia el markup, se recalibra
con la muestra que devuelve el diagnóstico. Parser tolerante a varias formas."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

BASE = "https://www.argenprop.com"
# La tarjeta de aviso puede venir con distintas clases según la versión del sitio.
CARD_SELECTORS = [
    "div.listing__item", "div.card", "li.listing__item",
    "div.card-container", "[data-item-card]", "div[data-qa='posting']",
]


def _norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def _txt(el: Any) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _int(s: str | None) -> int | None:
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def _tipo_de(texto: str) -> str | None:
    t = _norm(texto)
    if "casa" in t or "chalet" in t:
        return "casa"
    if "departamento" in t or "depto" in t or "ph" in t or "monoambiente" in t:
        return "departamento"
    if "terreno" in t or "lote" in t:
        return "terreno"
    if "campo" in t or "finca" in t or "chacra" in t or "quinta" in t:
        return "campo"
    return None


def _parse_card(card: Any, now: str) -> dict[str, Any]:
    a = card.select_one("a[href*='--'], a[href*='-venta-'], a[href*='/clasificado'], a[href]")
    href = (a.get("href") if a else "") or ""
    url = (BASE + href) if href.startswith("/") else (href or None)
    m = re.search(r"--(\d+)", href) or re.search(r"/(\d{5,})\b", href)
    listing_id = m.group(1) if m else None

    # Precio + moneda (varios contenedores posibles).
    ptxt = _txt(card.select_one("[class*='price'], .card__price, p.card__price, [data-qa='POSTING_CARD_PRICE']"))
    low = ptxt.lower()
    precio = _int(ptxt)
    if "usd" in low or "u$s" in low or "dolar" in low or "dólar" in low:
        moneda = "USD"
    elif "$" in ptxt or "peso" in low or "ars" in low:
        moneda = "ARS"
    else:
        moneda = None

    # Ubicación / título.
    titulo = (_txt(card.select_one(".card__title, [class*='title'], h2, h3"))
              or _txt(card.select_one(".card__address, [class*='address']")) or "Aviso Argenprop")
    direccion = _txt(card.select_one(".card__address, [class*='address']"))
    zona_txt = _txt(card.select_one(".card__title, .card__location, [class*='location']"))

    # Características (m², ambientes, dormitorios): suelen venir como lista de <li>.
    blob = _txt(card.select_one(".card__common-data, .card__main-features, [class*='features'], ul")) or _txt(card)
    m2 = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*m", blob))
    dorm = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*dormitor", _norm(blob)))
    amb = (lambda x: int(x.group(1)) if x else None)(re.search(r"(\d+)\s*ambiente", _norm(blob)))

    tipo = _tipo_de(f"{href} {titulo}")

    return {
        "source": "argenprop", "listing_id": listing_id, "titulo": titulo[:200], "url": url,
        "operacion": "venta", "tipo": tipo, "precio": precio, "moneda": moneda,
        "precio_usd": precio if moneda == "USD" else None,
        "m2_cubierta": m2, "m2_total": None, "ambientes": amb, "dormitorios": dorm,
        "provincia": "Mendoza", "departamento": zona_txt or direccion or None, "barrio": None,
        "lat": None, "lon": None, "fetched_at": now,
    }


def parse_cards(html: str, now: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Devuelve (filas, diagnóstico). El diagnóstico incluye la primera tarjeta
    cruda (o un fragmento del HTML si no encontró nada) para calibrar."""
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    soup = BeautifulSoup(html or "", "lxml")

    cards: list[Any] = []
    sel_ok = None
    for sel in CARD_SELECTORS:
        found = soup.select(sel)
        found = [c for c in found if c.select_one("a[href]")]
        if found:
            cards, sel_ok = found, sel
            break

    rows: list[dict[str, Any]] = []
    for c in cards:
        row = _parse_card(c, now)
        if row["listing_id"]:
            rows.append(row)

    diag: dict[str, Any] = {
        "selector": sel_ok, "tarjetas": len(cards), "parseados": len(rows),
        "titulo_pagina": _txt(soup.title)[:120],
    }
    if cards:
        diag["primera_tarjeta"] = str(cards[0])[:2200]
        if rows:
            diag["primer_parseado"] = rows[0]
    else:
        diag["html_muestra"] = (html or "")[:1200]
    return rows, diag
