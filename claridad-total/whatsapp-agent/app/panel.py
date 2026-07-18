"""Panel del corredor (Fase 1): leads calificados y visitas agendadas.

Server-rendered, sin dependencias de frontend. En producción va detrás de
autenticación (ver nota en el README) — en Fase 1 es de uso interno/local."""
from __future__ import annotations

import html
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import inventory, store

router = APIRouter()

_TEMP_COLOR = {"caliente": "#B23F2A", "tibio": "#9C6A15", "frio": "#6B7683"}
_TEMP_LABEL = {"caliente": "🔥 Caliente", "tibio": "🟡 Tibio", "frio": "⚪ Frío"}


@router.get("/panel/api/leads")
def api_leads() -> JSONResponse:
    return JSONResponse(store.list_leads())


@router.get("/panel/api/visitas")
def api_visitas() -> JSONResponse:
    return JSONResponse(store.list_visitas())


def _esc(v: Any) -> str:
    return html.escape(str(v)) if v is not None else "—"


def _lead_row(l: dict[str, Any]) -> str:
    temp = l.get("temperatura", "frio")
    color = _TEMP_COLOR.get(temp, "#6B7683")
    presu = f"US$ {int(l['presupuesto_usd']):,}".replace(",", ".") if l.get("presupuesto_usd") else "—"
    badge = _TEMP_LABEL.get(temp, temp)
    hand = ' <span class="tag hand">handoff</span>' if l.get("handoff") else ""
    return f"""<tr>
      <td><span class="pill" style="background:{color}1f;color:{color}">{badge}</span></td>
      <td><b>{_esc(l.get('nombre') or 'Sin nombre')}</b><br><span class="sub">{_esc(l.get('telefono') or l.get('wa_id'))}</span>{hand}</td>
      <td>{presu}</td>
      <td>{_esc(l.get('zona'))}</td>
      <td>{_esc(l.get('tipo'))}{(' · ' + str(l['ambientes']) + ' amb') if l.get('ambientes') else ''}</td>
      <td>{_esc(l.get('urgencia'))}</td>
      <td class="num">{_esc(l.get('score', 0))}</td>
    </tr>"""


def _visita_row(v: dict[str, Any]) -> str:
    return f"""<tr>
      <td><b>{_esc(v.get('fecha_hora'))}</b></td>
      <td>{_esc(v.get('propiedad'))}</td>
      <td>{_esc(v.get('nombre') or 'comprador')}<br><span class="sub">{_esc(v.get('telefono'))}</span></td>
    </tr>"""


@router.get("/panel", response_class=HTMLResponse)
def panel() -> HTMLResponse:
    leads = sorted(store.list_leads(), key=lambda x: x.get("score", 0), reverse=True)
    visitas = store.list_visitas()
    disp = [p for p in inventory.load() if p.get("estado") == "disponible"]

    n_cal = sum(1 for l in leads if l.get("temperatura") == "caliente")
    leads_html = "".join(_lead_row(l) for l in leads) or '<tr><td colspan="7" class="empty">Todavía no hay leads.</td></tr>'
    visitas_html = "".join(_visita_row(v) for v in visitas) or '<tr><td colspan="3" class="empty">Sin visitas agendadas.</td></tr>'

    return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel del corredor · Claridad Total</title>
<style>
  :root{{--bg:#F6F7F9;--card:#fff;--ink:#161D26;--soft:#3E4956;--mut:#6B7683;--line:#E1E6EB;--acc:#0C7C8C}}
  @media(prefers-color-scheme:dark){{:root{{--bg:#0E1319;--card:#151C24;--ink:#EAEEF2;--soft:#B9C3CD;--mut:#8A95A0;--line:#25303A;--acc:#3FC1D2}}}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:15px}}
  .wrap{{max-width:1000px;margin:0 auto;padding:20px 18px 60px}}
  header{{display:flex;align-items:center;gap:12px;margin-bottom:6px}}
  .dot{{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,var(--acc),#095B67);color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px;font-family:ui-monospace,monospace}}
  h1{{font-size:1.3rem;margin:0}} .lead{{color:var(--mut);font-size:.9rem;margin:2px 0 20px}}
  .stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}}
  .stat{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;min-width:120px}}
  .stat .f{{font-size:1.6rem;font-weight:700}} .stat .l{{font-size:.78rem;color:var(--mut)}}
  h2{{font-size:1.05rem;margin:26px 0 10px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
  table{{width:100%;border-collapse:collapse;font-size:.88rem}}
  th,td{{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top}}
  th{{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);background:color-mix(in srgb,var(--ink) 4%,var(--card))}}
  tr:last-child td{{border-bottom:0}}
  .sub{{color:var(--mut);font-size:.82em}} .num{{text-align:center;font-variant-numeric:tabular-nums;font-weight:600}}
  .pill{{font-size:.72rem;padding:3px 9px;border-radius:20px;white-space:nowrap;font-weight:600}}
  .tag.hand{{font-size:.66rem;background:#B23F2A22;color:#B23F2A;padding:1px 7px;border-radius:20px;margin-left:4px}}
  .empty{{text-align:center;color:var(--mut);padding:22px}}
  .foot{{margin-top:24px;font-size:.78rem;color:var(--mut)}}
  .refresh{{margin-left:auto;font-size:.8rem;color:var(--acc);text-decoration:none;border:1px solid var(--line);padding:6px 12px;border-radius:8px}}
</style></head><body><div class="wrap">
  <header><div class="dot">CT</div><h1>Panel del corredor</h1><a class="refresh" href="/panel">↻ Actualizar</a></header>
  <p class="lead">Leads calificados y visitas del agente de WhatsApp · Claridad Total</p>
  <div class="stats">
    <div class="stat"><div class="f">{len(leads)}</div><div class="l">Leads totales</div></div>
    <div class="stat"><div class="f" style="color:#B23F2A">{n_cal}</div><div class="l">Calientes 🔥</div></div>
    <div class="stat"><div class="f">{len(visitas)}</div><div class="l">Visitas agendadas</div></div>
    <div class="stat"><div class="f">{len(disp)}</div><div class="l">Propiedades disponibles</div></div>
  </div>
  <h2>Leads</h2>
  <div class="card"><table>
    <thead><tr><th>Temp.</th><th>Contacto</th><th>Presupuesto</th><th>Zona</th><th>Busca</th><th>Urgencia</th><th>Score</th></tr></thead>
    <tbody>{leads_html}</tbody>
  </table></div>
  <h2>Próximas visitas</h2>
  <div class="card"><table>
    <thead><tr><th>Cuándo</th><th>Propiedad</th><th>Comprador</th></tr></thead>
    <tbody>{visitas_html}</tbody>
  </table></div>
  <p class="foot">Fase 1 · Datos en vivo desde el agente. En producción este panel va detrás de login.
  APIs JSON: <code>/panel/api/leads</code> · <code>/panel/api/visitas</code></p>
</div></body></html>""")
