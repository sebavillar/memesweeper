export const dynamic = "force-dynamic";

import {
  api,
  qsMercado,
  type BreakdownRow,
  type Filtros,
  type Histogram,
  type ScatterPoint,
  type Summary,
} from "@/lib/api";
import { FilterBar } from "@/components/filter-bar";
import { Card, Kpi } from "@/components/ui";
import {
  DeptoBars,
  FuenteBars,
  PriceHistogram,
  ScatterTipos,
  TipoBars,
} from "@/components/charts";
import { fecha, n, usd } from "@/lib/format";

export default async function MercadoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const qs = qsMercado(sp);
  const q = qs ? `?${qs}` : "";
  const amp = qs ? `&${qs}` : "";

  const [filtros, summary, porDepto, porTipo, porFuente, histo, scatter] =
    await Promise.all([
      api<Filtros>("/api/v1/market/filters"),
      api<Summary>(`/api/v1/market/summary${q}`),
      api<BreakdownRow[]>(`/api/v1/market/breakdown?by=departamento${amp}`),
      api<BreakdownRow[]>(`/api/v1/market/breakdown?by=tipo${amp}`),
      api<BreakdownRow[]>(`/api/v1/market/breakdown?by=fuente${amp}`),
      api<Histogram>(`/api/v1/market/histogram${q}`),
      api<ScatterPoint[]>(`/api/v1/market/scatter${q}`),
    ]);

  return (
    <>
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl text-ink">Mercado</h1>
          <p className="mt-0.5 text-sm text-ink-2">
            Oferta real relevada de MercadoLibre, RE/MAX e Inmoclick ·
            actualizada {fecha(filtros.last_fetch)}
          </p>
        </div>
      </header>

      <FilterBar filtros={filtros} />

      <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Avisos en venta" value={n(summary.n)} hint={`${n(summary.con_m2)} con superficie`} />
        <Kpi label="Precio mediano" value={usd(summary.mediana_usd)} />
        <Kpi
          label="USD/m² mediano"
          value={n(summary.ppm_mediano)}
          hint={
            summary.ppm_p25
              ? `p25 ${n(summary.ppm_p25)} · p75 ${n(summary.ppm_p75)}`
              : undefined
          }
        />
        <Kpi label="Base total" value={n(filtros.total)} hint="todas las fuentes" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card
          title="USD/m² mediano por departamento"
          subtitle="Solo avisos con precio en USD y superficie"
        >
          <DeptoBars data={porDepto} />
        </Card>

        <Card
          title="Distribución de precios"
          subtitle="Avisos en venta (USD), recortado al p95"
        >
          <PriceHistogram data={histo} />
        </Card>

        <Card
          title="Precio vs. superficie"
          subtitle="Cada punto es un aviso · color por tipo"
          className="lg:col-span-2"
        >
          <ScatterTipos data={scatter} />
        </Card>

        <Card title="Avisos por tipo">
          <TipoBars data={porTipo} />
        </Card>

        <Card title="Avisos por fuente">
          <FuenteBars data={porFuente} />
        </Card>
      </div>
    </>
  );
}
