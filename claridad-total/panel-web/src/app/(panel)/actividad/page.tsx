export const dynamic = "force-dynamic";

import Link from "next/link";
import { api, type Actividad } from "@/lib/api";
import { Card, Kpi, SourcePill } from "@/components/ui";
import { n } from "@/lib/format";

function fechaLarga(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return isNaN(+d)
    ? iso
    : d.toLocaleDateString("es-AR", { weekday: "short", day: "2-digit", month: "short" });
}

export default async function ActividadPage() {
  const act = await api<Actividad>("/api/v1/market/activity?dias=30");
  const dias = act.dias;
  const totalNuevos = dias.reduce((s, d) => s + d.nuevos, 0);
  const totalCambios = dias.reduce((s, d) => s + d.cambios_precio, 0);
  const maxNuevos = Math.max(1, ...dias.map((d) => d.nuevos));

  return (
    <>
      <p className="mb-4 text-sm">
        <Link href="/" className="text-brand-ink hover:underline">← Mercado</Link>
      </p>
      <header className="mb-5">
        <h1 className="font-serif text-2xl text-ink">Actividad de la base</h1>
        <p className="mt-0.5 text-sm text-ink-2">
          Cómo se van agregando y modificando los avisos, día por día (últimos 30 días)
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Kpi label="Días con actividad" value={n(dias.length)} />
        <Kpi label="Altas (30 días)" value={n(totalNuevos)} hint="avisos nuevos detectados" />
        <Kpi label="Cambios de precio (30 días)" value={n(totalCambios)} />
      </div>

      <Card className="mt-4 overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-medium">Día</th>
              <th className="px-3 py-3 font-medium">Altas</th>
              <th className="px-3 py-3 font-medium">Por fuente</th>
              <th className="px-3 py-3 text-right font-medium">Cambios de precio</th>
              <th className="px-4 py-3 text-right font-medium">Stock visto</th>
            </tr>
          </thead>
          <tbody>
            {dias.map((d) => (
              <tr key={d.fecha} className="border-b border-hairline last:border-0">
                <td className="whitespace-nowrap px-4 py-2.5 capitalize text-ink">
                  {fechaLarga(d.fecha)}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="tnum w-8 font-semibold text-ink">{d.nuevos}</span>
                    <span
                      className="inline-block h-2 rounded-full bg-brand/60"
                      style={{ width: `${(d.nuevos / maxNuevos) * 120}px` }}
                    />
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(d.por_fuente)
                      .sort((a, b) => b[1] - a[1])
                      .map(([src, cnt]) => (
                        <span key={src} className="inline-flex items-center gap-1">
                          <SourcePill source={src} />
                          <span className="tnum text-xs text-muted">{cnt}</span>
                        </span>
                      ))}
                    {!Object.keys(d.por_fuente).length && <span className="text-muted">—</span>}
                  </div>
                </td>
                <td className="tnum px-3 py-2.5 text-right">
                  {d.cambios_precio > 0 ? (
                    <span className="rounded-full bg-gold/10 px-2 py-0.5 text-xs font-medium text-gold">
                      {d.cambios_precio}
                    </span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td className="tnum px-4 py-2.5 text-right text-ink-2">{n(d.vistos)}</td>
              </tr>
            ))}
            {!dias.length && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-muted">
                  Todavía no hay historial. Se va poblando con cada corrida de los scrapers.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <p className="mt-3 text-xs text-muted">
        <b>Altas</b>: avisos nuevos vistos por primera vez ese día. <b>Cambios de precio</b>:
        avisos ya conocidos cuyo precio en USD cambió. <b>Stock visto</b>: avisos relevados
        ese día (la última corrida marca el stock activo).
      </p>
    </>
  );
}
