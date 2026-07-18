"""Panel del corredor (Fase 1/2): leads, visitas y gestión de inventario.

Server-rendered, sin dependencias de frontend. Protegido por clave (PANEL_PASSWORD):
si está definida, el navegador pide usuario/clave (el usuario puede ser cualquiera)."""
from __future__ import annotations

import html
import re
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import inventory, store
from .config import settings

_security = HTTPBasic(auto_error=False)


def _auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    """Exige la clave del panel si PANEL_PASSWORD está configurada."""
    pw = settings.panel_password
    if not pw:
        return  # sin protección (desarrollo)
    if credentials is None or not secrets.compare_digest(credentials.password, pw):
        raise HTTPException(
            status_code=401, detail="No autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )


router = APIRouter(dependencies=[Depends(_auth)])

_TEMP_COLOR = {"caliente": "#B23F2A", "tibio": "#9C6A15", "frio": "#6B7683"}
_TEMP_LABEL = {"caliente": "🔥 Caliente", "tibio": "🟡 Tibio", "frio": "⚪ Frío"}
_EST_COLOR = {"disponible": "#2E7D5B", "reservada": "#9C6A15", "vendida": "#6B7683"}

_CSS = """
:root{--bg:#F6F7F9;--card:#fff;--ink:#161D26;--soft:#3E4956;--mut:#6B7683;--line:#E1E6EB;--acc:#0C7C8C}
@media(prefers-color-scheme:dark){:root{--bg:#0E1319;--card:#151C24;--ink:#EAEEF2;--soft:#B9C3CD;--mut:#8A95A0;--line:#25303A;--acc:#3FC1D2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:15px}
.wrap{max-width:1000px;margin:0 auto;padding:18px 16px 70px}
header{display:flex;align-items:center;gap:12px;margin-bottom:4px;flex-wrap:wrap}
.dot{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,var(--acc),#095B67);color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px;font-family:ui-monospace,monospace}
h1{font-size:1.25rem;margin:0}
nav{display:flex;gap:8px;margin:14px 0 20px}
nav a{font-size:.9rem;text-decoration:none;color:var(--soft);border:1px solid var(--line);padding:7px 14px;border-radius:8px;background:var(--card)}
nav a.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.lead{color:var(--mut);font-size:.88rem;margin:0 0 16px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 17px;min-width:110px}
.stat .f{font-size:1.5rem;font-weight:700}.stat .l{font-size:.76rem;color:var(--mut)}
h2{font-size:1.02rem;margin:24px 0 10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:.87rem}
th,td{text-align:left;padding:10px 13px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);background:color-mix(in srgb,var(--ink) 4%,var(--card))}
tr:last-child td{border-bottom:0}
.sub{color:var(--mut);font-size:.82em}.num{text-align:center;font-variant-numeric:tabular-nums;font-weight:600}
.pill{font-size:.72rem;padding:3px 9px;border-radius:20px;white-space:nowrap;font-weight:600}
.empty{text-align:center;color:var(--mut);padding:22px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
@media(max-width:640px){.grid,.grid3{grid-template-columns:1fr}}
label{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 4px;font-weight:600}
input,select,textarea{width:100%;font:inherit;font-size:.92rem;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:9px 11px}
textarea{min-height:64px;resize:vertical}
.field{margin-bottom:13px}
.chk{display:flex;align-items:center;gap:8px;margin-top:22px}.chk input{width:auto}
.btn{background:var(--acc);color:#fff;border:0;border-radius:9px;padding:11px 18px;font:inherit;font-weight:650;cursor:pointer}
.btn:hover{filter:brightness(1.06)}
.btn.sm{padding:5px 10px;font-size:.8rem;border-radius:7px}
.btn.gray{background:transparent;color:var(--soft);border:1px solid var(--line)}
.btn.danger{background:transparent;color:#B23F2A;border:1px solid color-mix(in srgb,#B23F2A 40%,transparent)}
.prop{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;padding:14px 16px;border-bottom:1px solid var(--line)}
.prop:last-child{border-bottom:0}
.prop h3{margin:0 0 3px;font-size:1rem}.prop .meta{font-size:.85rem;color:var(--soft)}
.prop .actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.inline{display:inline}
.foot{margin-top:22px;font-size:.76rem;color:var(--mut)}
"""


def _esc(v: Any) -> str:
    return html.escape(str(v)) if v is not None else "—"


def _page(title: str, active: str, body: str) -> HTMLResponse:
    nav = "".join(
        f'<a href="{href}" class="{"on" if active==key else ""}">{label}</a>'
        for key, href, label in [
            ("resumen", "/panel", "Resumen"),
            ("inventario", "/panel/inventario", "Inventario"),
        ]
    )
    return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>{_CSS}</style></head><body><div class="wrap">
<header><div class="dot">CT</div><h1>Panel del corredor</h1></header>
<nav>{nav}</nav>{body}
</div></body></html>""")


# ---------------- Resumen (leads + visitas) ----------------
@router.get("/panel/api/leads")
def api_leads() -> JSONResponse:
    return JSONResponse(store.list_leads())


@router.get("/panel/api/visitas")
def api_visitas() -> JSONResponse:
    return JSONResponse(store.list_visitas())


def _lead_row(l: dict[str, Any]) -> str:
    temp = l.get("temperatura", "frio")
    color = _TEMP_COLOR.get(temp, "#6B7683")
    presu = f"US$ {int(l['presupuesto_usd']):,}".replace(",", ".") if l.get("presupuesto_usd") else "—"
    hand = ' <span class="pill" style="background:#B23F2A22;color:#B23F2A">handoff</span>' if l.get("handoff") else ""
    return f"""<tr>
      <td><span class="pill" style="background:{color}1f;color:{color}">{_TEMP_LABEL.get(temp,temp)}</span></td>
      <td><b>{_esc(l.get('nombre') or 'Sin nombre')}</b><br><span class="sub">{_esc(l.get('telefono') or l.get('wa_id'))}</span>{hand}</td>
      <td>{presu}</td><td>{_esc(l.get('zona'))}</td>
      <td>{_esc(l.get('tipo'))}{(' · '+str(l['ambientes'])+' amb') if l.get('ambientes') else ''}</td>
      <td>{_esc(l.get('urgencia'))}</td><td class="num">{_esc(l.get('score',0))}</td></tr>"""


@router.get("/panel", response_class=HTMLResponse)
def panel() -> HTMLResponse:
    leads = sorted(store.list_leads(), key=lambda x: x.get("score", 0), reverse=True)
    visitas = store.list_visitas()
    disp = [p for p in inventory.load() if p.get("estado") == "disponible"]
    n_cal = sum(1 for l in leads if l.get("temperatura") == "caliente")
    leads_html = "".join(_lead_row(l) for l in leads) or '<tr><td colspan="7" class="empty">Todavía no hay leads.</td></tr>'
    vis_html = "".join(
        f'<tr><td><b>{_esc(v.get("fecha_hora"))}</b></td><td>{_esc(v.get("propiedad"))}</td>'
        f'<td>{_esc(v.get("nombre") or "comprador")}<br><span class="sub">{_esc(v.get("telefono"))}</span></td></tr>'
        for v in visitas
    ) or '<tr><td colspan="3" class="empty">Sin visitas agendadas.</td></tr>'
    body = f"""
    <p class="lead">Leads calificados y visitas del agente de WhatsApp</p>
    <div class="stats">
      <div class="stat"><div class="f">{len(leads)}</div><div class="l">Leads</div></div>
      <div class="stat"><div class="f" style="color:#B23F2A">{n_cal}</div><div class="l">Calientes 🔥</div></div>
      <div class="stat"><div class="f">{len(visitas)}</div><div class="l">Visitas</div></div>
      <div class="stat"><div class="f">{len(disp)}</div><div class="l">Disponibles</div></div>
    </div>
    <h2>Leads</h2><div class="card"><table>
      <thead><tr><th>Temp.</th><th>Contacto</th><th>Presup.</th><th>Zona</th><th>Busca</th><th>Urgencia</th><th>Score</th></tr></thead>
      <tbody>{leads_html}</tbody></table></div>
    <h2>Próximas visitas</h2><div class="card"><table>
      <thead><tr><th>Cuándo</th><th>Propiedad</th><th>Comprador</th></tr></thead>
      <tbody>{vis_html}</tbody></table></div>"""
    return _page("Panel · Resumen", "resumen", body)


# ---------------- Inventario (gestión) ----------------
def _num(v: str | None) -> int | None:
    digits = re.sub(r"\D", "", v or "")
    return int(digits) if digits else None


@router.get("/panel/inventario", response_class=HTMLResponse)
def inventario() -> HTMLResponse:
    props = inventory.load()
    rows = ""
    for p in props:
        est = p.get("estado", "disponible")
        color = _EST_COLOR.get(est, "#6B7683")
        opts = "".join(
            f'<option value="{e}" {"selected" if e==est else ""}>{e.capitalize()}</option>'
            for e in ("disponible", "reservada", "vendida")
        )
        precio = f"US$ {int(p.get('precio_usd') or 0):,}".replace(",", ".")
        rows += f"""<div class="prop">
          <div><h3>{_esc(p.get('titulo'))}</h3>
            <div class="meta">{precio} · {_esc(p.get('sup_cubierta'))} m² · {_esc(p.get('ambientes'))} amb ·
            {_esc(p.get('barrio') or p.get('departamento'))}
            {' · cochera' if p.get('cochera') else ''}</div>
            <div class="sub">{_esc(p.get('id'))}</div></div>
          <div class="actions">
            <span class="pill" style="background:{color}1f;color:{color}">{est.capitalize()}</span>
            <form class="inline" method="post" action="/panel/inventario/{p['id']}/estado">
              <select name="estado" class="btn sm gray" onchange="this.form.submit()">{opts}</select></form>
            <form class="inline" method="post" action="/panel/inventario/{p['id']}/eliminar"
                  onsubmit="return confirm('¿Eliminar esta propiedad?')">
              <button class="btn sm danger">Eliminar</button></form>
          </div></div>"""
    lista = rows or '<div class="empty">Todavía no hay propiedades. Cargá la primera abajo 👇</div>'
    body = f"""
    <p class="lead">Cargá, editá y dá de baja tus propiedades. Los cambios impactan al instante en el agente.</p>
    <h2>Propiedades ({len(props)})</h2>
    <div class="card">{lista}</div>
    <h2>Agregar propiedad</h2>
    <div class="card" style="padding:18px">
      <form method="post" action="/panel/inventario/nueva">
        <div class="field"><label>Título (opcional, se arma solo)</label>
          <input name="titulo" placeholder="Depto 3 amb · Godoy Cruz centro"></div>
        <div class="grid3">
          <div class="field"><label>Tipo</label><select name="tipo">
            <option value="departamento">Departamento</option><option value="casa">Casa</option></select></div>
          <div class="field"><label>Departamento / zona</label><input name="departamento" placeholder="Godoy Cruz"></div>
          <div class="field"><label>Barrio</label><input name="barrio" placeholder="Bombal"></div>
        </div>
        <div class="grid3">
          <div class="field"><label>Precio (US$)</label><input name="precio_usd" inputmode="numeric" placeholder="112000"></div>
          <div class="field"><label>Expensas (US$)</label><input name="expensas_usd" inputmode="numeric" placeholder="40"></div>
          <div class="field"><label>Ambientes</label><input name="ambientes" inputmode="numeric" placeholder="3"></div>
        </div>
        <div class="grid3">
          <div class="field"><label>Sup. cubierta (m²)</label><input name="sup_cubierta" inputmode="numeric" placeholder="78"></div>
          <div class="field"><label>Sup. total (m²)</label><input name="sup_total" inputmode="numeric" placeholder="78"></div>
          <div class="field"><label>Dormitorios</label><input name="dormitorios" inputmode="numeric" placeholder="2"></div>
        </div>
        <div class="grid3">
          <div class="field"><label>Baños</label><input name="banos" inputmode="numeric" placeholder="1"></div>
          <div class="field"><label>Antigüedad (años)</label><input name="antiguedad" inputmode="numeric" placeholder="8"></div>
          <div class="field chk"><input type="checkbox" name="cochera" id="cochera"><label for="cochera" style="margin:0">Cochera</label></div>
        </div>
        <div class="field"><label>Características (separadas por coma)</label>
          <input name="caracteristicas" placeholder="balcón, luminoso, amenities"></div>
        <div class="field"><label>Descripción</label>
          <textarea name="descripcion" placeholder="Luminoso, orientación norte, a 3 cuadras del parque..."></textarea></div>
        <div class="grid">
          <div class="field"><label>Estado legal (resumen)</label><input name="estado_legal_resumen" placeholder="Título al día"></div>
          <div class="field"><label>Fotos (URLs públicas, separadas por coma)</label><input name="fotos" placeholder="https://..."></div>
        </div>
        <div class="grid">
          <div class="field"><label>Asesor (nombre)</label><input name="asesor_nombre" placeholder="Sebastián"></div>
          <div class="field"><label>Asesor (teléfono)</label><input name="asesor_telefono" placeholder="5492610000001"></div>
        </div>
        <button class="btn" type="submit">Guardar propiedad</button>
      </form>
    </div>
    <p class="foot">Las fotos deben ser URLs públicas (https). La carga de imágenes desde el celular llega en la próxima mejora.</p>"""
    return _page("Panel · Inventario", "inventario", body)


@router.post("/panel/inventario/nueva")
async def inventario_nueva(request: Request) -> RedirectResponse:
    f = await request.form()

    def s(k: str) -> str:
        return str(f.get(k) or "").strip()

    def lst(k: str) -> list[str]:
        return [x.strip() for x in s(k).split(",") if x.strip()]

    tipo = s("tipo") or "departamento"
    barrio, depto = s("barrio"), s("departamento")
    ambientes = _num(f.get("ambientes")) or 0
    titulo = s("titulo") or f"{tipo.capitalize()} {ambientes} amb · {barrio or depto or 'Mendoza'}"
    prop = {
        "estado": "disponible", "tipo": tipo, "operacion": "venta",
        "titulo": titulo, "departamento": depto, "barrio": barrio,
        "direccion_aprox": barrio or depto,
        "precio_usd": _num(f.get("precio_usd")) or 0,
        "expensas_usd": _num(f.get("expensas_usd")),
        "sup_cubierta": _num(f.get("sup_cubierta")) or 0,
        "sup_total": _num(f.get("sup_total")) or _num(f.get("sup_cubierta")) or 0,
        "ambientes": ambientes,
        "dormitorios": _num(f.get("dormitorios")),
        "banos": _num(f.get("banos")),
        "antiguedad": _num(f.get("antiguedad")),
        "cochera": f.get("cochera") == "on",
        "caracteristicas": lst("caracteristicas"),
        "descripcion": s("descripcion"),
        "estado_legal_resumen": s("estado_legal_resumen"),
        "fotos": lst("fotos"),
        "asesor": {"nombre": s("asesor_nombre"), "telefono": s("asesor_telefono")},
    }
    inventory.add(prop)
    return RedirectResponse("/panel/inventario", status_code=303)


@router.post("/panel/inventario/{prop_id}/estado")
async def inventario_estado(prop_id: str, request: Request) -> RedirectResponse:
    f = await request.form()
    estado = str(f.get("estado") or "disponible")
    if estado in ("disponible", "reservada", "vendida"):
        inventory.set_estado(prop_id, estado)
    return RedirectResponse("/panel/inventario", status_code=303)


@router.post("/panel/inventario/{prop_id}/eliminar")
def inventario_eliminar(prop_id: str) -> RedirectResponse:
    inventory.delete(prop_id)
    return RedirectResponse("/panel/inventario", status_code=303)
