#!/usr/bin/env python3
"""Explorador automático de la API de InmoUp: prueba muchas formas de filtro
hasta que 'total' > 0, y muestra la combinación ganadora + el primer aviso.

Corre en el servidor (tiene salida a internet). No necesita nada instalado
salvo Python 3. Uso:  python3 inmoup_probe.py
"""
import json
import urllib.request
import urllib.parse
import base64
import itertools
import re

BASE = "https://inmoup.com.ar/api/2.0"
AUTH = "Basic " + base64.b64encode(b"developer:Up0358").decode()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA, "Accept": "application/json", "Authorization": AUTH}


def _req(url, data=None):
    body = None
    hdrs = dict(HDRS)
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs,
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:150]


def _total(txt):
    m = re.search(r'"total":\s*(\d+)', txt or "")
    return int(m.group(1)) if m else None


def _lista(txt):
    """Encuentra la primera lista de dicts que parezcan avisos dentro del JSON."""
    try:
        d = json.loads(txt)
    except Exception:  # noqa: BLE001
        return None, None
    def walk(x, path=""):
        if isinstance(x, list) and x and isinstance(x[0], dict):
            keys = set(x[0])
            if keys & {"precio", "price", "titulo", "title", "id", "inm_id", "direccion"}:
                return path, x
        if isinstance(x, dict):
            for k, v in x.items():
                r = walk(v, f"{path}.{k}")
                if r:
                    return r
        if isinstance(x, list):
            for i, v in enumerate(x):
                r = walk(v, f"{path}[{i}]")
                if r:
                    return r
        return None
    got = walk(d)
    return (got[0], got[1]) if got else (None, None)


ganadores = []


def probar(desc, url, data=None):
    st, txt = _req(url, data)
    tot = _total(txt)
    marca = ""
    if tot and tot > 0:
        marca = f"  <<< GANADOR total={tot}"
        ganadores.append((desc, url, data, txt))
    print(f"[{st}] tot={tot} {desc}{marca}")


print("=" * 60)
print("EXPLORADOR API INMOUP — probando formatos de filtro")
print("=" * 60)

# 1) GET con slug directo en la ruta (varias variantes de path)
for slug in ["casas-en-venta", "inmuebles-en-venta", "casas-en-venta-en-mendoza",
             "venta/casas", "casas/venta"]:
    probar(f"GET /inmuebles/{slug}", f"{BASE}/inmuebles/{slug}")
    probar(f"GET /inmuebles/buscar/{slug}", f"{BASE}/inmuebles/buscar/{slug}")

# 2) GET buscar con query params sueltos
for k, v in [("grupo", 1), ("grupo_tip_id", 1), ("grupo_tip", 1), ("operacion", 1),
             ("operacion_id", 1), ("op", 1), ("tipo_operacion", 1), ("q", "casas-en-venta"),
             ("query", "casas-en-venta"), ("busqueda", "casas-en-venta"), ("term", "casas")]:
    probar(f"GET buscar?{k}={v}", f"{BASE}/inmuebles/buscar?{urllib.parse.urlencode({k: v})}")

# 3) POST con distintos esquemas de "filtros"
op_vals = [1, 2, "1", "2", "venta", [1], ["venta"]]
grp_vals = [1, [1], "1", "casas"]
for op, grp in itertools.product(op_vals, grp_vals):
    for opkey in ("operacion", "operacion_id", "op", "tipo_operacion"):
        for grpkey in ("grupo", "grupo_tip_id", "grupo_tip"):
            body = {"filtros": {opkey: op, grpkey: grp}, "page": 1, "limit": 30}
            probar(f"POST filtros{{{opkey}={op!r},{grpkey}={grp!r}}}", f"{BASE}/inmuebles/buscar", body)

# 4) POST con provincia/ubicacion agregada al mejor candidato
for extra in ({"provincia": 1}, {"provincia": "mendoza"}, {"provincia_id": 1},
              {"ubicacion": "mendoza"}, {"localidad": "mendoza"}):
    body = {"filtros": {"operacion": 1, "grupo": 1, **extra}, "page": 1, "limit": 30}
    probar(f"POST +{extra}", f"{BASE}/inmuebles/buscar", body)

# 5) POST con filtros como listas (formato de checkboxes)
for body in [
    {"filtros": {"operaciones": [1], "grupos": [1]}, "page": 1, "limit": 30},
    {"filtros": {"operacion": [1], "grupo": [1], "provincia": [1]}, "page": 1},
    {"operacion": 1, "grupo": 1, "page": 1, "limit": 30},
    {"filtros": {}, "operacion": 1, "grupo_tip_id": 1, "page": 1},
    {"filtros": {"condiciones": {"operacion": 1}}, "page": 1},
]:
    probar(f"POST {json.dumps(body, ensure_ascii=False)[:60]}", f"{BASE}/inmuebles/buscar", body)

print("\n" + "=" * 60)
if ganadores:
    desc, url, data, txt = ganadores[0]
    print("✅ FORMATO QUE FUNCIONA:")
    print("  desc:", desc)
    print("  url :", url)
    print("  body:", json.dumps(data, ensure_ascii=False) if data else "(GET)")
    path, items = _lista(txt)
    print(f"  lista de avisos en: {path} ({len(items) if items else 0} items)")
    if items:
        print("  CLAVES primer aviso:", sorted(items[0].keys()))
        print("  PRIMER AVISO:", json.dumps(items[0], ensure_ascii=False)[:1400])
else:
    print("❌ Ninguna combinación devolvió avisos.")
    print("Pegá igual TODA la salida de arriba (los [200] con sus tot=) para analizar.")
print("=" * 60)
