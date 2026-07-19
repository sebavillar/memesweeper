export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { api, type LeadDetail } from "@/lib/api";
import { Card, TempPill } from "@/components/ui";
import { fecha, hace, usd } from "@/lib/format";

export default async function ConsultaDetail({
  params,
}: {
  params: Promise<{ wa_id: string }>;
}) {
  const { wa_id } = await params;
  let d: LeadDetail;
  try {
    d = await api<LeadDetail>(`/api/v1/leads/${encodeURIComponent(wa_id)}`);
  } catch {
    notFound();
  }
  const { lead: l, conversacion, visitas } = d;

  const perfil: [string, string][] = [
    ["Presupuesto", l.presupuesto_usd ? usd(l.presupuesto_usd) : "—"],
    ["Zona", l.zona || "—"],
    ["Tipo", l.tipo || "—"],
    ["Ambientes", l.ambientes ? String(l.ambientes) : "—"],
    ["Urgencia", l.urgencia || "—"],
    ["Crédito", l.necesita_credito ? "Sí" : "—"],
    ["Mensajes", String(l.mensajes)],
    ["Primer contacto", fecha(l.creado)],
  ];

  return (
    <>
      <p className="mb-4 text-sm">
        <Link href="/consultas" className="text-brand-ink hover:underline">← Consultas</Link>
      </p>

      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl text-ink">{l.nombre || "Sin nombre"}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-ink-2">
            <TempPill t={l.temperatura} />
            <span className="tnum">score {l.score}</span>
            <span className="text-muted">· última actividad {hace(l.actualizado)}</span>
          </p>
        </div>
        {l.wa_link && (
          <a
            href={l.wa_link}
            target="_blank"
            rel="noopener"
            className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink"
          >
            💬 Abrir chat en WhatsApp
          </a>
        )}
      </header>

      {l.handoff && (
        <div className="mb-4 rounded-xl border border-[#d03b3b]/30 bg-[#d03b3b]/5 px-4 py-3 text-sm text-ink">
          <b className="text-[#b23f2a]">Pidió hablar con vos</b>
          {l.handoff_motivo ? ` — ${l.handoff_motivo}` : ""}. Respondele desde WhatsApp.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card title="Perfil del comprador">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              {perfil.map(([k, v]) => (
                <div key={k}>
                  <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{k}</dt>
                  <dd className="mt-0.5 text-sm text-ink">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 border-t border-hairline pt-3 text-xs text-muted">
              Teléfono: {l.telefono}
            </p>
          </Card>

          {visitas.length > 0 && (
            <Card title="Visitas" className="mt-4">
              <ul className="space-y-2">
                {visitas.map((v, i) => (
                  <li key={i} className="text-sm">
                    <span className="font-medium text-ink">{v.fecha_hora}</span>
                    <span className="text-ink-2"> · {v.propiedad || v.propiedad_id}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div className="lg:col-span-2">
          <Card title="Conversación con el agente" subtitle={`${conversacion.length} mensajes`}>
            {conversacion.length ? (
              <div className="space-y-3">
                {conversacion.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-start" : "justify-end"}`}>
                    <div
                      className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
                        m.role === "user"
                          ? "rounded-tl-sm bg-page text-ink"
                          : "rounded-tr-sm bg-brand/10 text-ink"
                      }`}
                    >
                      <span className="mb-0.5 block text-[10px] uppercase tracking-wide text-muted">
                        {m.role === "user" ? "Comprador" : "Agente"}
                      </span>
                      {m.text}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-muted">Sin mensajes registrados.</p>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
