"""Panel del corredor: leads, visitas y gestión de inventario (con fotos, estadísticas
y análisis por inmueble). Protegido por clave (PANEL_PASSWORD)."""
from __future__ import annotations

import html
import os
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import analysis, db, images, inventory, store
from .config import settings

_MEDIA_DIR = Path(os.environ.get("DATA_DIR") or "data") / "media"


def _media_base() -> str:
    dom = settings.agent_domain
    return f"https://{dom}/media" if dom else "/media"


_security = HTTPBasic(auto_error=False)


def _auth(credentials: HTTPBasicCredentials = Depends(_security)) -> None:
    pw = settings.panel_password
    if not pw:
        return
    if credentials is None or not secrets.compare_digest(credentials.password, pw):
        raise HTTPException(status_code=401, detail="No autorizado",
                            headers={"WWW-Authenticate": "Basic"})


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
.btn{background:var(--acc);color:#fff;border:0;border-radius:9px;padding:11px 18px;font:inherit;font-weight:650;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{filter:brightness(1.06)}
.btn.sm{padding:5px 10px;font-size:.8rem;border-radius:7px}
.btn.gray{background:transparent;color:var(--soft);border:1px solid var(--line)}
.btn.danger{background:transparent;color:#B23F2A;border:1px solid color-mix(in srgb,#B23F2A 40%,transparent)}
.prop{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;padding:14px 16px;border-bottom:1px solid var(--line)}
.prop:last-child{border-bottom:0}
.prop h3{margin:0 0 3px;font-size:1rem}.prop .meta{font-size:.85rem;color:var(--soft)}
.prop .actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.inline{display:inline}
.thumb{width:130px;height:98px;object-fit:cover;border-radius:8px;border:1px solid var(--line);display:block}
.photo{position:relative}
.photo form{position:absolute;top:5px;right:5px}
.photo .del{background:rgba(0,0,0,.6);color:#fff;border:0;border-radius:50%;width:24px;height:24px;cursor:pointer;font-size:14px;line-height:1}
.foot{margin-top:22px;font-size:.76rem;color:var(--mut)}
"""


def _esc(v: Any) -> str:
    return html.escape(str(v)) if v is not None else "—"


def _money(n: Any) -> str:
    return f"US$ {int(n or 0):,}".replace(",", ".")


def _page(title: str, active: str, body: str) -> HTMLResponse:
    nav = "".join(
        f'<a href="{href}" class="{"on" if active==key else ""}">{label}</a>'
        for key, href, label in [("resumen", "/panel", "Resumen"),
                                  ("inventario", "/panel/inventario", "Inventario")]
    )
    return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>{_CSS}</style></head><body><div class="wrap">
<header><div class="dot">CT</div><h1>Panel del corredor</h1></header>
<nav>{nav}</nav>{body}
</div></body></html>""")


# ---------------- Resumen ----------------
@router.get("/panel/api/leads")
def api_leads() -> JSONResponse:
    return JSONResponse(store.list_leads())


@router.get("/panel/api/visitas")
def api_visitas() -> JSONResponse:
    return JSONResponse(store.list_visitas())


def _lead_row(l: dict[str, Any]) -> str:
    temp = l.get("temperatura", "frio")
    color = _TEMP_COLOR.get(temp, "#6B7683")
    presu = _money(l["presupuesto_usd"]) if l.get("presupuesto_usd") else "—"
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


# ---------------- Inventario ----------------
def _num(v: Any) -> int | None:
    digits = re.sub(r"\D", "", str(v or ""))
    return int(digits) if digits else None


def _fv(p: dict[str, Any] | None, k: str) -> str:
    if not p or p.get(k) in (None, ""):
        return ""
    return html.escape(str(p.get(k)))


def _form_fields(p: dict[str, Any] | None = None) -> str:
    tipo = (p or {}).get("tipo", "departamento")
    cochera = "checked" if (p and p.get("cochera")) else ""
    carac = html.escape(", ".join((p or {}).get("caracteristicas") or []))
    asesor = (p or {}).get("asesor", {}) if p else {}
    an = html.escape(str(asesor.get("nombre", "") or ""))
    at = html.escape(str(asesor.get("telefono", "") or ""))
    return f"""
      <div class="field"><label>Título (opcional, se arma solo)</label>
        <input name="titulo" value="{_fv(p,'titulo')}" placeholder="Depto 3 amb · Godoy Cruz centro"></div>
      <div class="grid3">
        <div class="field"><label>Tipo</label><select name="tipo">
          <option value="departamento" {"selected" if tipo=="departamento" else ""}>Departamento</option>
          <option value="casa" {"selected" if tipo=="casa" else ""}>Casa</option></select></div>
        <div class="field"><label>Departamento / zona</label><input name="departamento" value="{_fv(p,'departamento')}" placeholder="Godoy Cruz"></div>
        <div class="field"><label>Barrio</label><input name="barrio" value="{_fv(p,'barrio')}" placeholder="Bombal"></div>
      </div>
      <div class="grid3">
        <div class="field"><label>Precio (US$)</label><input name="precio_usd" value="{_fv(p,'precio_usd')}" inputmode="numeric" placeholder="112000"></div>
        <div class="field"><label>Expensas (US$)</label><input name="expensas_usd" value="{_fv(p,'expensas_usd')}" inputmode="numeric" placeholder="40"></div>
        <div class="field"><label>Ambientes</label><input name="ambientes" value="{_fv(p,'ambientes')}" inputmode="numeric" placeholder="3"></div>
      </div>
      <div class="grid3">
        <div class="field"><label>Sup. cubierta (m²)</label><input name="sup_cubierta" value="{_fv(p,'sup_cubierta')}" inputmode="numeric" placeholder="78"></div>
        <div class="field"><label>Sup. total (m²)</label><input name="sup_total" value="{_fv(p,'sup_total')}" inputmode="numeric" placeholder="78"></div>
        <div class="field"><label>Dormitorios</label><input name="dormitorios" value="{_fv(p,'dormitorios')}" inputmode="numeric" placeholder="2"></div>
      </div>
      <div class="grid3">
        <div class="field"><label>Baños</label><input name="banos" value="{_fv(p,'banos')}" inputmode="numeric" placeholder="1"></div>
        <div class="field"><label>Antigüedad (años)</label><input name="antiguedad" value="{_fv(p,'antiguedad')}" inputmode="numeric" placeholder="8"></div>
        <div class="field chk"><input type="checkbox" name="cochera" id="cochera" {cochera}><label for="cochera" style="margin:0">Cochera</label></div>
      </div>
      <div class="field"><label>Características (separadas por coma)</label>
        <input name="caracteristicas" value="{carac}" placeholder="balcón, luminoso, amenities"></div>
      <div class="field"><label>Descripción</label>
        <textarea name="descripcion" placeholder="Luminoso, orientación norte...">{_fv(p,'descripcion')}</textarea></div>
      <div class="field"><label>Agregar fotos (desde tu dispositivo · se convierten a JPG)</label>
        <input type="file" name="fotos_files" accept="image/*" multiple></div>
      <div class="grid">
        <div class="field"><label>Estado legal (resumen)</label><input name="estado_legal_resumen" value="{_fv(p,'estado_legal_resumen')}" placeholder="Título al día"></div>
        <div class="field"><label>Asesor (nombre)</label><input name="asesor_nombre" value="{an}" placeholder="Sebastián"></div>
      </div>
      <div class="field"><label>Asesor (teléfono)</label><input name="asesor_telefono" value="{at}" placeholder="5492610000001"></div>"""


def _fields_from_form(f: Any) -> dict[str, Any]:
    def s(k: str) -> str:
        return str(f.get(k) or "").strip()

    def lst(k: str) -> list[str]:
        return [x.strip() for x in s(k).split(",") if x.strip()]

    tipo = s("tipo") or "departamento"
    barrio, depto = s("barrio"), s("departamento")
    ambientes = _num(f.get("ambientes")) or 0
    titulo = s("titulo") or f"{tipo.capitalize()} {ambientes} amb · {barrio or depto or 'Mendoza'}"
    return {
        "tipo": tipo, "operacion": "venta", "titulo": titulo,
        "departamento": depto, "barrio": barrio, "direccion_aprox": barrio or depto,
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
        "asesor": {"nombre": s("asesor_nombre"), "telefono": s("asesor_telefono")},
    }


async def _save_uploaded(files: list[Any], prop_id: str, existing: list[str]) -> list[str]:
    """Convierte cada foto subida a JPG y devuelve la lista de URLs (existentes + nuevas)."""
    urls = list(existing or [])
    i = len(urls)
    for uf in files:
        fn = getattr(uf, "filename", "") or ""
        if not fn:
            continue
        data = await uf.read()
        if not data:
            continue
        i += 1
        dest = _MEDIA_DIR / f"{prop_id}-{i}.jpg"
        while dest.exists():
            i += 1
            dest = _MEDIA_DIR / f"{prop_id}-{i}.jpg"
        if images.to_jpeg(data, dest):
            urls.append(f"{_media_base()}/{dest.name}")
    return urls


@router.get("/panel/inventario", response_class=HTMLResponse)
def inventario() -> HTMLResponse:
    props = inventory.load()
    rows = ""
    for p in props:
        est = p.get("estado", "disponible")
        color = _EST_COLOR.get(est, "#6B7683")
        opts = "".join(f'<option value="{e}" {"selected" if e==est else ""}>{e.capitalize()}</option>'
                       for e in ("disponible", "reservada", "vendida"))
        st = store.get_prop_stats(p["id"])
        nfotos = len(p.get("fotos") or [])
        rows += f"""<div class="prop">
          <div><h3><a href="/panel/inventario/{p['id']}" style="color:inherit;text-decoration:none">{_esc(p.get('titulo'))} ›</a></h3>
            <div class="meta">{_money(p.get('precio_usd'))} · {_esc(p.get('sup_cubierta'))} m² · {_esc(p.get('ambientes'))} amb ·
            {_esc(p.get('barrio') or p.get('departamento'))}{' · cochera' if p.get('cochera') else ''}</div>
            <div class="sub">{_esc(p.get('id'))} · {nfotos} 📷 · ofrecida {st.get('ofrecida',0)}× · fichas {st.get('ficha',0)} · visitas {st.get('visitas',0)}</div></div>
          <div class="actions">
            <span class="pill" style="background:{color}1f;color:{color}">{est.capitalize()}</span>
            <a class="btn sm gray" href="/panel/inventario/{p['id']}/editar">Editar</a>
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
      <form method="post" action="/panel/inventario/nueva" enctype="multipart/form-data">
        {_form_fields(None)}
        <button class="btn" type="submit">Guardar propiedad</button>
      </form>
    </div>"""
    return _page("Panel · Inventario", "inventario", body)


@router.get("/panel/inventario/{prop_id}/editar", response_class=HTMLResponse)
def inventario_editar_form(prop_id: str) -> HTMLResponse:
    p = inventory.get(prop_id)
    if not p:
        return _page("No encontrada", "inventario",
                     '<p class="lead">Propiedad no encontrada. <a href="/panel/inventario">← Volver</a></p>')
    fotos = p.get("fotos") or []
    fotos_html = "".join(
        f'<div class="photo"><img class="thumb" src="{html.escape(u)}" alt="">'
        f'<form method="post" action="/panel/inventario/{prop_id}/foto/eliminar" onsubmit="return confirm(\'¿Borrar esta foto?\')">'
        f'<input type="hidden" name="url" value="{html.escape(u)}"><button class="del" title="Borrar">✕</button></form></div>'
        for u in fotos
    ) or '<span class="sub">Sin fotos.</span>'
    body = f"""
    <p class="lead"><a href="/panel/inventario/{prop_id}">← Volver al inmueble</a></p>
    <h2>Editar: {_esc(p.get('titulo'))}</h2>
    <h2 style="font-size:.9rem">Fotos actuales</h2>
    <div class="card" style="padding:14px"><div style="display:flex;gap:10px;flex-wrap:wrap">{fotos_html}</div></div>
    <h2>Datos</h2>
    <div class="card" style="padding:18px">
      <form method="post" action="/panel/inventario/{prop_id}/editar" enctype="multipart/form-data">
        {_form_fields(p)}
        <button class="btn" type="submit">Guardar cambios</button>
      </form>
    </div>"""
    return _page(f"Editar · {p.get('titulo')}", "inventario", body)


@router.get("/panel/inventario/{prop_id}", response_class=HTMLResponse)
def inventario_detalle(prop_id: str) -> HTMLResponse:
    p = inventory.get(prop_id)
    if not p:
        return _page("No encontrada", "inventario",
                     '<p class="lead">Propiedad no encontrada. <a href="/panel/inventario">← Volver</a></p>')
    st = store.get_prop_stats(prop_id)
    val = analysis.valuar(p)
    fotos = p.get("fotos") or []
    fotos_html = "".join(f'<img class="thumb" src="{html.escape(u)}" alt="">' for u in fotos) \
        or '<span class="sub">Sin fotos cargadas todavía.</span>'

    datos = [
        ("Precio publicado", _money(p.get("precio_usd"))), ("Tipo", (p.get("tipo") or "").capitalize()),
        ("Zona", p.get("barrio") or p.get("departamento")), ("Sup. cubierta", f"{_esc(p.get('sup_cubierta'))} m²"),
        ("Sup. total", f"{_esc(p.get('sup_total'))} m²"), ("Ambientes", p.get("ambientes")),
        ("Dormitorios", p.get("dormitorios")), ("Baños", p.get("banos")),
        ("Antigüedad", f"{_esc(p.get('antiguedad'))} años"), ("Cochera", "Sí" if p.get("cochera") else "No"),
        ("Expensas", _money(p.get("expensas_usd")) if p.get("expensas_usd") else "—"),
        ("Estado legal", p.get("estado_legal_resumen") or "—"),
    ]
    datos_html = "".join(
        f'<div><div class="sub" style="text-transform:uppercase;font-size:.68rem;letter-spacing:.05em">{_esc(k)}</div>'
        f'<div style="font-weight:600">{_esc(v)}</div></div>' for k, v in datos
    )
    stat_cards = "".join(
        f'<div class="stat"><div class="f">{st.get(m,0)}</div><div class="l">{lbl}</div></div>'
        for m, lbl in [("ofrecida", "Veces ofrecida"), ("ficha", "Fichas enviadas"), ("visitas", "Visitas agendadas")]
    )
    wf = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--line)">'
        f'<span class="sub">{_esc(fac["label"])} · {_esc(fac["detalle"])}</span>'
        f'<b>{_money(fac["val"]) if fac["label"].startswith("Base") else ("+" if fac["val"]>=0 else "−")+_money(abs(fac["val"]))}</b></div>'
        for fac in val["factores"]
    )
    comp_rows = ""
    for c in val["comparables"]:
        if c.get("source") == "mercadolibre" and c.get("url"):
            titulo = (f'<a href="{html.escape(c["url"])}" target="_blank" rel="noopener" style="color:var(--acc)">{_esc(c["titulo"])}</a>'
                      ' <span class="pill" style="background:#9C6A151f;color:#9C6A15">ML</span>')
        else:
            titulo = (f'<a href="/panel/inventario/{c["id"]}" style="color:var(--acc)">{_esc(c["titulo"])}</a>'
                      ' <span class="sub">· propio</span>')
        comp_rows += (f'<tr><td>{titulo}</td><td>{_money(c["precio_usd"])}</td>'
                      f'<td>{_money(c["ppm"])}/m²</td><td>{_esc(c["estado"])}</td></tr>')
    comps = comp_rows or '<tr><td colspan="4" class="empty">Sin comparables todavía. Actualizá la oferta de MercadoLibre.</td></tr>'
    mkt = db.stats()
    mkt_note = (f"Base de oferta: {mkt['venta_usd']} publicaciones en venta (US$) · última actualización {mkt['last_fetch']}"
                if mkt.get("last_fetch") else
                "Todavía no cargaste oferta de MercadoLibre. Corré la actualización para calibrar con datos reales.")

    body = f"""
    <p class="lead"><a href="/panel/inventario">← Volver</a> &nbsp;·&nbsp; <a href="/panel/inventario/{prop_id}/editar">✏️ Editar</a></p>
    <h2 style="margin-top:6px">{_esc(p.get('titulo'))}</h2>
    <div class="sub" style="margin-bottom:14px">{_esc(p.get('id'))} · {(p.get('estado') or '').capitalize()}</div>
    <div class="card" style="padding:16px;margin-bottom:16px">
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{fotos_html}</div>
      <div class="grid3" style="gap:14px">{datos_html}</div>
      {('<p style="margin:14px 0 0">'+_esc(p.get('descripcion'))+'</p>') if p.get('descripcion') else ''}
    </div>
    <h2>Estadísticas del inmueble</h2>
    <div class="stats">{stat_cards}</div>
    <p class="foot">Métricas del agente de WhatsApp: veces ofrecida a compradores, fichas enviadas y visitas agendadas.</p>
    <h2>Análisis de mercado <span class="pill" style="background:#9C6A151f;color:#9C6A15">estimación</span></h2>
    <div class="card" style="padding:18px">
      <div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-end">
        <div><div class="sub" style="text-transform:uppercase;font-size:.68rem">Valor estimado de cierre</div>
          <div style="font-size:2rem;font-weight:700;color:var(--acc)">{_money(val['valor'])}</div>
          <div class="sub">Rango {_money(val['low'])} — {_money(val['high'])} · {_money(val['ppm'])}/m²</div></div>
        <div><div class="sub" style="text-transform:uppercase;font-size:.68rem">Confianza</div>
          <div style="font-size:1.4rem;font-weight:700">{val['confianza']}%</div><div class="sub">{val['n_comparables']} comparables</div></div>
        <div><div class="sub" style="text-transform:uppercase;font-size:.68rem">Oferta sugerida</div>
          <div style="font-size:1.4rem;font-weight:700">{_money(val['oferta_sugerida'])}</div><div class="sub">+12% s/ cierre</div></div>
      </div>
      <div style="margin-top:16px"><div class="sub" style="text-transform:uppercase;font-size:.68rem;margin-bottom:6px">Cómo se construye</div>{wf}</div>
      <div style="margin-top:16px"><div class="sub" style="text-transform:uppercase;font-size:.68rem;margin-bottom:6px">Comparables (tu inventario)</div>
        <table><thead><tr><th>Propiedad</th><th>Precio</th><th>US$/m²</th><th>Estado</th></tr></thead><tbody>{comps}</tbody></table></div>
    </div>
    <p class="foot">{mkt_note}. Fuente de oferta: <b>MercadoLibre</b> (API oficial).</p>"""
    return _page(f"Inmueble · {p.get('titulo')}", "inventario", body)


@router.post("/panel/inventario/nueva")
async def inventario_nueva(request: Request) -> RedirectResponse:
    f = await request.form()
    prop = {**_fields_from_form(f), "estado": "disponible", "fotos": []}
    prop = inventory.add(prop)
    urls = await _save_uploaded(f.getlist("fotos_files"), prop["id"], [])
    if urls:
        inventory.update(prop["id"], {"fotos": urls})
    return RedirectResponse("/panel/inventario", status_code=303)


@router.post("/panel/inventario/{prop_id}/editar")
async def inventario_editar(prop_id: str, request: Request) -> RedirectResponse:
    p = inventory.get(prop_id)
    if not p:
        return RedirectResponse("/panel/inventario", status_code=303)
    f = await request.form()
    inventory.update(prop_id, _fields_from_form(f))
    urls = await _save_uploaded(f.getlist("fotos_files"), prop_id, p.get("fotos") or [])
    inventory.update(prop_id, {"fotos": urls})
    return RedirectResponse(f"/panel/inventario/{prop_id}", status_code=303)


@router.post("/panel/inventario/{prop_id}/foto/eliminar")
async def inventario_foto_eliminar(prop_id: str, request: Request) -> RedirectResponse:
    f = await request.form()
    url = str(f.get("url") or "")
    p = inventory.get(prop_id)
    if p and url:
        inventory.update(prop_id, {"fotos": [u for u in (p.get("fotos") or []) if u != url]})
        if "/media/" in url:
            try:
                (_MEDIA_DIR / url.split("/media/")[-1]).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
    return RedirectResponse(f"/panel/inventario/{prop_id}/editar", status_code=303)


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
