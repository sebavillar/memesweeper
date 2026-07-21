#!/usr/bin/env python3
"""Descubre cómo pagina la API de MendozaProp.

La API ignora `page` (devuelve siempre los mismos 20 avisos). Este probe:
  1) Muestra la estructura de la respuesta (claves de nivel superior + cualquier
     metadato de paginación tipo total/last_page/per_page).
  2) Prueba distintos nombres de parámetro (page/pagina/offset/limit/…) y reporta
     con cuál CAMBIA el primer aviso → ese es el que sirve para avanzar/traer más.

Uso:
    docker compose exec app python -m scripts.probe_mendozaprop
"""
from __future__ import annotations

import json

import httpx

from app.mendozaprop import API, OP_VENTA, UA, _items


def _get(params: dict) -> httpx.Response:
    return httpx.get(API, params={"operationType": OP_VENTA, **params},
                     headers={"User-Agent": UA, "Accept": "application/json"},
                     timeout=30, follow_redirects=True)


def _ids(payload) -> list:
    return [it.get("id") for it in _items(payload)]


def main() -> int:
    # --- 1) Estructura de la respuesta base ---
    r0 = _get({})
    p0 = r0.json()
    print("=== ESTRUCTURA (respuesta base, sin paginar) ===")
    if isinstance(p0, dict):
        print("claves nivel superior:", list(p0.keys()))
        # metadatos típicos de paginación en cualquier nivel
        for k in ("total", "count", "last_page", "current_page", "per_page",
                  "perPage", "pageSize", "next_page_url", "hasMore", "meta",
                  "pagination", "totalPages", "totalCount"):
            if k in p0:
                v = p0[k]
                print(f"  {k} = {json.dumps(v, ensure_ascii=False)[:200]}")
    else:
        print("la respuesta es una LISTA (no dict) de", len(p0), "elementos")

    base_ids = _ids(p0)
    print(f"\nbase: {len(base_ids)} items · primer id = {base_ids[0] if base_ids else None}")

    # --- 2) Probar candidatos de paginación ---
    # value 2 = 'segunda página'; para offset/skip/start usamos 20 (tamaño de página).
    candidatos = [
        ("page", 2), ("pagina", 2), ("p", 2), ("pageNumber", 2), ("n_page", 2),
        ("offset", 20), ("skip", 20), ("start", 20), ("from", 20),
        ("per_page", 100), ("perPage", 100), ("limit", 100), ("pageSize", 100),
        ("take", 100), ("size", 100),
    ]
    print("\n=== PRUEBA DE PARÁMETROS ===")
    print("(buscamos: primer id DISTINTO al base = sirve para avanzar; "
          "o cantidad > 20 = sirve para traer más)\n")
    for nombre, val in candidatos:
        try:
            rr = _get({nombre: val})
            ids = _ids(rr.json())
        except Exception as exc:  # noqa: BLE001
            print(f"  {nombre}={val:<5} → ERROR {str(exc)[:60]}")
            continue
        primer = ids[0] if ids else None
        cambio = "≠ base ✅" if (primer is not None and primer != (base_ids[0] if base_ids else None)) else "= base"
        mas = "  ⬆ MÁS DE 20 ✅" if len(ids) > 20 else ""
        print(f"  {nombre}={val:<5} → {len(ids):>3} items · primer id={primer} · {cambio}{mas}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
