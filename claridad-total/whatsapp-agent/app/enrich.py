"""Enriquecimiento de comparables: ANTIGÜEDAD desde la ficha de cada aviso.

Los listados que barremos (ML/RE/MAX/Inmoclick) no traen la antigüedad; está en
la ficha de cada aviso. Visitar 1.800 fichas de golpe sería triplicar el tráfico,
así que el enfoque es GRADUAL y de bajo riesgo:

  - por día y por fuente, se visitan hasta N fichas pendientes (las más nuevas
    primero), con pausas largas entre pedidos;
  - cada ficha se marca como visitada (detail_at) aunque no traiga el dato,
    para no repetir pedidos nunca;
  - tras el barrido inicial (~2 semanas), solo quedan los avisos nuevos del día.

La extracción es un regex tolerante sobre el HTML ("Antigüedad ... N años", o
"a estrenar" → 0). Si una fuente no expone el dato en su ficha, el diagnóstico
lo muestra y se recalibra (mismo flujo que los scrapers)."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from . import db

log = logging.getLogger("enrich")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# "Antigüedad: 25 años" / "Antigüedad</th><td>25" / "25 años de antigüedad"
_RE_ANT = re.compile(r"antig[uü]edad\D{0,120}?(\d{1,3})\s*año", re.I | re.S)
_RE_ANT_INV = re.compile(r"(\d{1,3})\s*años?\s+de\s+antig[uü]edad", re.I)
_RE_ESTRENAR = re.compile(r"antig[uü]edad\D{0,120}?a\s+estrenar|\ba\s+estrenar\b", re.I | re.S)


def _get(url: str) -> httpx.Response:
    return httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9",
                                   "Accept": "text/html,application/xhtml+xml"},
                     timeout=30, follow_redirects=True)


def extraer_antiguedad(html: str) -> float | None:
    m = _RE_ANT.search(html) or _RE_ANT_INV.search(html)
    if m:
        v = int(m.group(1))
        return float(v) if 0 <= v <= 150 else None
    if _RE_ESTRENAR.search(html):
        return 0.0
    return None


def run(per_source: int = 60, pausa: float = 4.0) -> dict[str, Any]:
    """Visita fichas pendientes y guarda la antigüedad. Devuelve diagnóstico."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    diag: dict[str, Any] = {"fuentes": {}}

    for src in ("mercadolibre", "remax", "inmoclick"):
        filas = db.pending_detail(src, per_source)
        con_dato = sin_dato = errores = 0
        muestra: dict[str, Any] | None = None

        for f in filas:
            try:
                r = _get(f["url"])
            except Exception as exc:  # noqa: BLE001
                errores += 1
                if muestra is None:
                    muestra = {"url": f["url"], "error": str(exc)[:120]}
                # error de red: NO marcamos detail_at; se reintenta otro día
                if errores >= 3:
                    break  # la fuente parece caída hoy; no insistir
                continue

            if r.status_code != 200:
                # aviso dado de baja (404/410) u otro estado: marcar para no reintentar
                db.set_detail(src, f["listing_id"], None, now)
                errores += 1
                if muestra is None:
                    muestra = {"url": f["url"], "status": r.status_code}
                time.sleep(pausa)
                continue

            ant = extraer_antiguedad(r.text)
            db.set_detail(src, f["listing_id"], ant, now)
            if ant is not None:
                con_dato += 1
            else:
                sin_dato += 1
                if muestra is None:
                    # contexto alrededor de "antig" (si existe) para calibrar
                    i = r.text.lower().find("antig")
                    muestra = {"url": f["url"],
                               "contexto": re.sub(r"\s+", " ", r.text[i:i + 220]) if i >= 0
                               else "la ficha no menciona antigüedad"}
            time.sleep(pausa)

        diag["fuentes"][src] = {"visitadas": len(filas), "con_dato": con_dato,
                                "sin_dato": sin_dato, "errores": errores, "muestra": muestra}

    tot = sum(v["con_dato"] for v in diag["fuentes"].values())
    log.info("Enriquecimiento de fichas: %d antigüedades nuevas.", tot)
    return diag
