export const dynamic = "force-dynamic";

import Link from "next/link";
import { api, type Lead, type LeadSummary, type Visita } from "@/lib/api";
import { Card, Kpi, TempPill } from "@/components/ui";
import { hace, n, usd } from "@/lib/format";

export default async function ConsultasPage() {
  const [leads, summary, visitas] = await Promise.all([
    api<Lead[]>("/api/v1/leads"),
    api<LeadSummary>("/api/v1/leads/summary"),
    api<Visita[]>("/api/v1/visitas"),
  ]);

  return (
    <>
      <header className="mb-5">
        <h1 className="font-serif text-2xl text-ink">Consultas</h1>
        <p className="mt-0.5 text-sm text-ink-2">
          Compradores que escribieron al agente de WhatsApp, calificados automáticamente
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Consultas totales" value={n(summary.total)} hint={`${n(summary.calientes)} calientes · ${n(summary.tibios)} tibias`} />
        <Kpi label="🔥 Calientes" value={n(summary.calientes)} hint="listas para llamar" />
        <Kpi label="Visitas agendadas" value={n(summary.visitas)} />
        <Kpi label="Derivadas a vos" value={n(summary.handoffs)} hint="pidieron hablar con humano" />
      </div>

      <h2 className="mb-3 mt-7 font-serif text-lg text-ink">Leads</h2>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-medium">Comprador</th>
              <th className="px-3 py-3 font-medium">Temperatura</th>
              <th className="px-3 py-3 text-right font-medium">Score</th>
              <th className="px-3 py-3 text-right font-medium">Presupuesto</th>
              <th className="px-3 py-3 font-medium">Busca</th>
              <th className="px-3 py-3 font-medium">Urgencia</th>
              <th className="px-3 py-3 font-medium">Estado</th>
              <th className="px-4 py-3 text-right font-medium">Última</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.wa_id} className="border-b border-hairline last:border-0 hover:bg-page/60">
                <td className="px-4 py-2.5">
                  <Link href={`/consultas/${encodeURIComponent(l.wa_id)}`} className="font-medium text-brand-ink hover:underline">
                    {l.nombre || "Sin nombre"}
                  </Link>
                  <div className="text-xs text-muted">
                    {l.telefono}
                    {l.ultimo_mensaje && (
                      <span className="ml-1 italic">· “{truncar(l.ultimo_mensaje.text, 40)}”</span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-2.5"><TempPill t={l.temperatura} /></td>
                <td className="tnum px-3 py-2.5 text-right font-semibold">{l.score}</td>
                <td className="tnum px-3 py-2.5 text-right">{l.presupuesto_usd ? usd(l.presupuesto_usd) : "—"}</td>
                <td className="px-3 py-2.5 text-ink-2">
                  {[l.tipo, l.zona].filter(Boolean).join(" · ") || "—"}
                </td>
                <td className="px-3 py-2.5 text-ink-2">{l.urgencia || "—"}</td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {l.visita_agendada && (
                      <span className="rounded-full bg-[#0ca30c]/10 px-2 py-0.5 text-[10px] font-semibold text-[#0a7d0a]">visita</span>
                    )}
                    {l.handoff && (
                      <span className="rounded-full bg-[#d03b3b]/10 px-2 py-0.5 text-[10px] font-semibold text-[#b23f2a]">derivado</span>
                    )}
                    {l.necesita_credito && (
                      <span className="rounded-full bg-page px-2 py-0.5 text-[10px] text-muted">crédito</span>
                    )}
                  </div>
                </td>
                <td className="tnum px-4 py-2.5 text-right text-muted">{hace(l.actualizado)}</td>
              </tr>
            ))}
            {!leads.length && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-muted">
                  Todavía no entraron consultas. Cuando un comprador le escriba al bot, aparece acá.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      {visitas.length > 0 && (
        <>
          <h2 className="mb-3 mt-7 font-serif text-lg text-ink">Próximas visitas</h2>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-hairline text-left text-[11px] uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-medium">Propiedad</th>
                  <th className="px-3 py-3 font-medium">Cuándo</th>
                  <th className="px-3 py-3 font-medium">Comprador</th>
                  <th className="px-4 py-3 font-medium">Teléfono</th>
                </tr>
              </thead>
              <tbody>
                {visitas.map((v, i) => (
                  <tr key={i} className="border-b border-hairline last:border-0">
                    <td className="px-4 py-2.5 text-ink">{v.propiedad || v.propiedad_id}</td>
                    <td className="px-3 py-2.5 font-medium text-ink">{v.fecha_hora}</td>
                    <td className="px-3 py-2.5 text-ink-2">{v.nombre || "—"}</td>
                    <td className="px-4 py-2.5 text-ink-2">
                      {v.wa_id ? (
                        <a href={`https://wa.me/${v.wa_id}`} target="_blank" rel="noopener" className="text-brand-ink hover:underline">
                          {v.telefono || v.wa_id}
                        </a>
                      ) : (v.telefono || "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}

function truncar(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + "…" : s;
}
