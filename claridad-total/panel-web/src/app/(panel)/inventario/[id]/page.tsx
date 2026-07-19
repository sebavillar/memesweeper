export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound } from "next/navigation";
import { api, type Prop, type Valuacion } from "@/lib/api";
import { Card, EstadoPill, Kpi, SourcePill } from "@/components/ui";
import { n, usd } from "@/lib/format";

type Detail = { prop: Prop; stats: Record<string, number>; valuacion: Valuacion };

export default async function FichaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let d: Detail;
  try {
    d = await api<Detail>(`/api/v1/inventory/${encodeURIComponent(id)}`);
  } catch {
    notFound();
  }
  const { prop: p, stats, valuacion: v } = d;

  const datos: [string, string][] = [
    ["Tipo", p.tipo || "—"],
    ["Zona", [p.barrio, p.departamento].filter(Boolean).join(", ") || "—"],
    ["Sup. cubierta", p.sup_cubierta ? `${n(p.sup_cubierta)} m²` : "—"],
    ["Sup. total", p.sup_total ? `${n(p.sup_total)} m²` : "—"],
    ["Ambientes", p.ambientes ? String(p.ambientes) : "—"],
    ["Dormitorios", p.dormitorios ? String(p.dormitorios) : "—"],
    ["Antigüedad", p.antiguedad != null ? `${p.antiguedad} años` : "—"],
    ["Cochera", p.cochera ? "Sí" : "No"],
  ];

  return (
    <>
      <p className="mb-4 text-sm">
        <Link href="/inventario" className="text-brand-ink hover:underline">
          ← Inventario
        </Link>
      </p>

      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl text-ink">{p.titulo}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-ink-2">
            <span className="tnum">{p.id}</span>
            <EstadoPill estado={p.estado} />
            <span className="tnum text-lg font-semibold text-brand-ink">
              {usd(p.precio_usd)}
            </span>
          </p>
        </div>
        <a
          href={`/panel/inventario/${p.id}/editar`}
          className="rounded-lg border border-hairline bg-surface px-3 py-1.5 text-sm text-ink-2 hover:text-ink"
        >
          ✏️ Editar
        </a>
      </header>

      {p.fotos && p.fotos.length > 0 && (
        <div className="mb-4 flex gap-2 overflow-x-auto">
          {p.fotos.map((f) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={f}
              src={f}
              alt=""
              className="h-36 rounded-xl border border-hairline object-cover"
            />
          ))}
        </div>
      )}

      <Card>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          {datos.map(([k, val]) => (
            <div key={k}>
              <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">
                {k}
              </dt>
              <dd className="mt-0.5 text-sm text-ink">{val}</dd>
            </div>
          ))}
        </dl>
        {p.descripcion && (
          <p className="mt-4 border-t border-hairline pt-4 text-sm leading-relaxed text-ink-2">
            {p.descripcion}
          </p>
        )}
      </Card>

      <h2 className="mb-3 mt-7 font-serif text-lg text-ink">
        Actividad del agente de WhatsApp
      </h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Veces ofrecida" value={n(stats.ofrecida || 0)} />
        <Kpi label="Fichas enviadas" value={n(stats.ficha || 0)} />
        <Kpi label="Visitas agendadas" value={n(stats.visitas || 0)} />
        <Kpi label="Consultas" value={n(stats.consultas || 0)} />
      </div>

      <h2 className="mb-3 mt-7 font-serif text-lg text-ink">
        Análisis de mercado{" "}
        <span className="ml-1 rounded-full bg-gold/10 px-2 py-0.5 align-middle text-[11px] font-medium text-gold">
          estimación
        </span>
      </h2>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
            Valor estimado de cierre
          </p>
          <p className="tnum mt-1 text-3xl font-semibold text-brand-ink">
            {usd(v.valor)}
          </p>
          <p className="mt-1 text-xs text-ink-2">
            Rango {usd(v.low)} — {usd(v.high)} · {n(v.ppm)}/m²
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-hairline pt-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted">
                Oferta sugerida
              </p>
              <p className="tnum mt-0.5 text-lg font-semibold text-ink">
                {usd(v.oferta_sugerida)}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted">
                Confianza
              </p>
              <p className="tnum mt-0.5 text-lg font-semibold text-ink">
                {v.confianza}%
              </p>
            </div>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-muted">
            {v.fuentes.valuacion} · comparables: {v.fuentes.comparables}
          </p>
        </Card>

        <Card title="Cómo se construye el valor" className="lg:col-span-2">
          <ul className="divide-y divide-hairline">
            {v.factores.map((f) => (
              <li
                key={f.label}
                className="flex items-baseline justify-between gap-3 py-2 text-sm"
              >
                <span className="text-ink-2">
                  <span className="font-medium text-ink">{f.label}</span>{" "}
                  · {f.detalle}
                </span>
                <span className="tnum font-medium text-ink">
                  {f.label.startsWith("Base")
                    ? usd(f.val)
                    : `${f.val >= 0 ? "+" : "−"}${usd(Math.abs(f.val)).slice(0)}`}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Comparables" subtitle="Oferta real de la zona + inventario propio" className="mt-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="py-2 pr-3 font-medium">Propiedad</th>
              <th className="px-3 py-2 font-medium">Fuente</th>
              <th className="px-3 py-2 text-right font-medium">Precio</th>
              <th className="px-3 py-2 text-right font-medium">USD/m²</th>
              <th className="py-2 pl-3 text-right font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {v.comparables.map((c) => (
              <tr
                key={`${c.source}-${c.id}`}
                className="border-b border-hairline last:border-0"
              >
                <td className="max-w-80 truncate py-2.5 pr-3">
                  {c.url ? (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener"
                      className="text-brand-ink hover:underline"
                    >
                      {c.titulo}
                    </a>
                  ) : c.source === "propio" ? (
                    <Link
                      href={`/inventario/${c.id}`}
                      className="text-brand-ink hover:underline"
                    >
                      {c.titulo}
                    </Link>
                  ) : (
                    c.titulo
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <SourcePill source={c.source} />
                </td>
                <td className="tnum px-3 py-2.5 text-right">{usd(c.precio_usd)}</td>
                <td className="tnum px-3 py-2.5 text-right text-ink-2">
                  {c.ppm ? n(c.ppm) : "—"}
                </td>
                <td className="py-2.5 pl-3 text-right text-ink-2">{c.estado}</td>
              </tr>
            ))}
            {!v.comparables.length && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-muted">
                  Sin comparables todavía.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </>
  );
}
