"use client";

/** Gráficos del panel (Recharts), según el sistema de diseño:
 *  - marcas finas, extremos de dato redondeados (4px) anclados a la línea base
 *  - grilla recesiva (hairline), un solo eje, texto en tinta (nunca color de serie)
 *  - tooltip en todas las formas; leyenda cuando hay ≥2 series
 *  - paleta validada (all-pairs PASS): teal, dorado, violeta, rosa */

import { useRouter, useSearchParams } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { AgeData, BreakdownRow, Histogram, PrivadoGap, ScatterPoint } from "@/lib/api";
import { compact, fecha, n, usd } from "@/lib/format";

const INK = "#1d1c1a";
const INK2 = "#52514e";
const MUTED = "#898781";
const HAIRLINE = "#e3e1da";
const SURFACE = "#fcfcfb";
const S = ["#0993ab", "#9c6a15", "#7a5bd0", "#d54f74"]; // serie validada

const AXIS = { fill: MUTED, fontSize: 11 } as const;

function Tip({
  rows,
  title,
}: {
  rows: { label: string; value: string; swatch?: string }[];
  title?: string;
}) {
  return (
    <div className="rounded-lg border border-hairline bg-surface px-3 py-2 text-xs shadow-sm">
      {title && <p className="mb-1 font-medium text-ink">{title}</p>}
      {rows.map((r) => (
        <p key={r.label} className="flex items-center gap-1.5 text-ink-2">
          {r.swatch && (
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: r.swatch }}
            />
          )}
          {r.label}: <span className="tnum font-medium text-ink">{r.value}</span>
        </p>
      ))}
    </div>
  );
}

/* ── USD/m² por departamento (barras horizontales, un matiz) ─────────────── */
export function DeptoBars({ data }: { data: BreakdownRow[] }) {
  const rows = data.filter((d) => d.ppm_mediano).slice(0, 12);
  if (!rows.length) return <Empty />;
  const h = Math.max(180, rows.length * 34);
  return (
    <div style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 44 }}>
          <CartesianGrid horizontal={false} stroke={HAIRLINE} />
          <XAxis
            type="number"
            tick={AXIS}
            tickFormatter={compact}
            axisLine={{ stroke: HAIRLINE }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="grupo"
            width={110}
            tick={{ fill: INK2, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(9,147,171,0.06)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={String(payload[0].payload.grupo)}
                  rows={[
                    { label: "USD/m² mediano", value: usd(payload[0].payload.ppm_mediano) },
                    { label: "Avisos", value: n(payload[0].payload.n) },
                    { label: "Mediana", value: usd(payload[0].payload.mediana_usd) },
                  ]}
                />
              ) : null
            }
          />
          <Bar dataKey="ppm_mediano" fill={S[0]} radius={[0, 4, 4, 0]} barSize={16}>
            <LabelList
              dataKey="ppm_mediano"
              position="right"
              formatter={(v) => n(Number(v))}
              style={{ fill: INK2, fontSize: 11, fontVariantNumeric: "tabular-nums" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── Histograma de distribución (un matiz). unidad:
      "usd" → precios totales (eje compacto 85k/1,2M)
      "ppm" → USD/m² (X = precio por m², Y = cantidad de avisos) ───────────── */
export function PriceHistogram({
  data,
  unidad = "usd",
  clickable = false,
}: {
  data: Histogram;
  unidad?: "usd" | "ppm";
  clickable?: boolean;
}) {
  const router = useRouter();
  const sp = useSearchParams();
  if (!data.buckets.length) return <Empty />;
  const fmt = unidad === "ppm" ? (v: number) => n(v) : compact;
  const rows = data.buckets.map((b) => ({
    ...b,
    rango: `${fmt(b.desde)}–${fmt(b.hasta)}`,
  }));

  // Clic en una barra (solo en el histograma de precios USD) → abre esos avisos.
  const abrir = clickable && unidad === "usd"
    ? (bucket: { desde: number; hasta: number }) => {
        const p = new URLSearchParams();
        for (const k of ["depto", "tipo", "fuente", "privado"]) {
          const v = sp.get(k);
          if (v) p.set(k, v);
        }
        p.set("usd_min", String(Math.floor(bucket.desde)));
        p.set("usd_max", String(Math.ceil(bucket.hasta)));
        router.push(`/avisos?${p.toString()}`);
      }
    : undefined;

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8 }}>
          <CartesianGrid vertical={false} stroke={HAIRLINE} />
          <XAxis
            dataKey="desde"
            tick={AXIS}
            tickFormatter={fmt}
            axisLine={{ stroke: HAIRLINE }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} width={34} />
          <Tooltip
            cursor={{ fill: "rgba(9,147,171,0.06)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={
                    unidad === "ppm"
                      ? `${payload[0].payload.rango} US$/m²`
                      : `US$ ${payload[0].payload.rango}`
                  }
                  rows={[{ label: "Avisos", value: n(payload[0].payload.n) }]}
                />
              ) : null
            }
          />
          <Bar
            dataKey="n"
            fill={S[0]}
            radius={[4, 4, 0, 0]}
            cursor={abrir ? "pointer" : undefined}
            onClick={abrir ? ((_: unknown, i: number) => abrir(rows[i])) as never : undefined}
          />
        </BarChart>
      </ResponsiveContainer>
      {abrir && (
        <p className="mt-1 text-[11px] text-muted">
          Tocá una barra para ver los avisos de ese rango de precio.
        </p>
      )}
      {data.recortados > 0 && (
        <p className="mt-1 text-[11px] text-muted">
          {data.recortados} avisos por encima del p95 quedan fuera del gráfico.
        </p>
      )}
    </div>
  );
}

/* ── Avisos por tipo (barras horizontales, un matiz) ─────────────────────── */
export function TipoBars({ data }: { data: BreakdownRow[] }) {
  const rows = data.slice(0, 8);
  if (!rows.length) return <Empty />;
  return (
    <div style={{ height: Math.max(160, rows.length * 32) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 40 }}>
          <CartesianGrid horizontal={false} stroke={HAIRLINE} />
          <XAxis type="number" tick={AXIS} axisLine={{ stroke: HAIRLINE }} tickLine={false} />
          <YAxis
            type="category"
            dataKey="grupo"
            width={110}
            tick={{ fill: INK2, fontSize: 12, textTransform: "capitalize" } as never}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(156,106,21,0.07)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={String(payload[0].payload.grupo)}
                  rows={[
                    { label: "Avisos", value: n(payload[0].payload.n) },
                    { label: "Mediana", value: usd(payload[0].payload.mediana_usd) },
                    { label: "USD/m² mediano", value: n(payload[0].payload.ppm_mediano) },
                  ]}
                />
              ) : null
            }
          />
          <Bar dataKey="n" fill={S[1]} radius={[0, 4, 4, 0]} barSize={14}>
            <LabelList
              dataKey="n"
              position="right"
              formatter={(v) => n(Number(v))}
              style={{ fill: INK2, fontSize: 11, fontVariantNumeric: "tabular-nums" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── Precio vs superficie (dispersión, categórica ≤4 series) ─────────────── */
const TIPOS_SCATTER = ["casa", "departamento", "terreno", "campo"] as const;

export function ScatterTipos({ data }: { data: ScatterPoint[] }) {
  const series = TIPOS_SCATTER.map((t, i) => ({
    tipo: t,
    color: S[i],
    pts: data.filter((p) => p.tipo === t),
  })).filter((s) => s.pts.length);
  if (!series.length) return <Empty />;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12 }}>
          <CartesianGrid stroke={HAIRLINE} />
          <XAxis
            type="number"
            dataKey="m2"
            name="m²"
            tick={AXIS}
            axisLine={{ stroke: HAIRLINE }}
            tickLine={false}
            label={{ value: "m² cubiertos", position: "insideBottomRight", dy: 10, fill: MUTED, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="usd"
            name="USD"
            tick={AXIS}
            tickFormatter={compact}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <ZAxis range={[42, 42]} />
          <Tooltip
            cursor={{ strokeDasharray: "4 4", stroke: MUTED }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={String(payload[0].payload.tipo ?? "aviso")}
                  rows={[
                    { label: "Precio", value: usd(payload[0].payload.usd) },
                    { label: "Superficie", value: `${n(payload[0].payload.m2)} m²` },
                    { label: "Zona", value: payload[0].payload.depto ?? "—" },
                  ]}
                />
              ) : null
            }
          />
          <Legend
            iconType="circle"
            iconSize={9}
            formatter={(v: string) => (
              <span style={{ color: INK2, fontSize: 12, textTransform: "capitalize" }}>{v}</span>
            )}
          />
          {series.map((s) => (
            <Scatter
              key={s.tipo}
              name={s.tipo}
              data={s.pts}
              fill={s.color}
              fillOpacity={0.78}
              stroke={SURFACE}
              strokeWidth={1.5}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── Precio por m² según antigüedad (dispersión + mediana por banda) ─────── */
export function AgePpmChart({ data }: { data: AgeData }) {
  if (data.points.length < 5) {
    return (
      <div className="flex h-40 items-center justify-center px-6 text-center text-sm text-muted">
        Muestra chica todavía ({data.n} avisos con antigüedad). El enriquecimiento
        diario de fichas la va completando solo.
      </div>
    );
  }
  const linea = data.bandas.map((b) => ({ edad: b.edad, ppm: b.ppm, banda: b.banda, n: b.n }));
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12 }}>
          <CartesianGrid stroke={HAIRLINE} />
          <XAxis
            type="number"
            dataKey="edad"
            name="antigüedad"
            tick={AXIS}
            axisLine={{ stroke: HAIRLINE }}
            tickLine={false}
            label={{ value: "antigüedad (años)", position: "insideBottomRight", dy: 10, fill: MUTED, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="ppm"
            name="USD/m²"
            tick={AXIS}
            tickFormatter={(v: number) => n(v)}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <ZAxis range={[36, 36]} />
          <Tooltip
            cursor={{ strokeDasharray: "4 4", stroke: MUTED }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                payload[0].payload.banda ? (
                  <Tip
                    title={`Banda ${payload[0].payload.banda} años`}
                    rows={[
                      { label: "USD/m² mediano", value: n(payload[0].payload.ppm), swatch: S[1] },
                      { label: "Avisos", value: n(payload[0].payload.n) },
                    ]}
                  />
                ) : (
                  <Tip
                    title={String(payload[0].payload.tipo ?? "aviso")}
                    rows={[
                      { label: "Antigüedad", value: `${n(payload[0].payload.edad)} años` },
                      { label: "USD/m²", value: n(payload[0].payload.ppm) },
                      { label: "Zona", value: payload[0].payload.depto ?? "—" },
                    ]}
                  />
                )
              ) : null
            }
          />
          <Legend
            iconType="circle"
            iconSize={9}
            formatter={(v: string) => <span style={{ color: INK2, fontSize: 12 }}>{v}</span>}
          />
          <Scatter
            name="Avisos"
            data={data.points}
            fill={S[0]}
            fillOpacity={0.55}
            stroke={SURFACE}
            strokeWidth={1}
          />
          <Scatter
            name="Mediana por edad"
            data={linea}
            fill={S[1]}
            line={{ stroke: S[1], strokeWidth: 2 }}
            stroke={SURFACE}
            strokeWidth={1.5}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── Diferencial barrio privado vs abierto (barras agrupadas) ────────────── */
export function PrivadoGapBars({ data }: { data: PrivadoGap }) {
  const g = data.global;
  if (!g.ppm_privado || !g.ppm_abierto) {
    return (
      <div className="flex h-40 items-center justify-center px-6 text-center text-sm text-muted">
        Todavía no hay muestra suficiente de avisos en barrio privado para comparar.
      </div>
    );
  }
  const rows = data.por_depto.length
    ? data.por_depto.slice(0, 8)
    : [{ ...g, grupo: "Mendoza (global)" }];
  return (
    <div>
      {g.gap_pct != null && (
        <p className="mb-3 text-sm text-ink-2">
          El m² en barrio privado vale{" "}
          <b className="text-ink">
            {g.gap_pct >= 0 ? "+" : ""}
            {g.gap_pct}%
          </b>{" "}
          que en barrio abierto: <span className="tnum">{usd(g.ppm_privado)}</span> vs{" "}
          <span className="tnum">{usd(g.ppm_abierto)}</span> el m² (mediana,{" "}
          {n(g.n_privado)} vs {n(g.n_abierto)} avisos).
        </p>
      )}
      <div style={{ height: Math.max(150, rows.length * 52) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 44 }}>
            <CartesianGrid horizontal={false} stroke={HAIRLINE} />
            <XAxis type="number" tick={AXIS} tickFormatter={(v: number) => n(v)} axisLine={{ stroke: HAIRLINE }} tickLine={false} />
            <YAxis
              type="category"
              dataKey="grupo"
              width={110}
              tick={{ fill: INK2, fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(9,147,171,0.06)" }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <Tip
                    title={String(payload[0].payload.grupo)}
                    rows={[
                      { label: "Privado", value: `${usd(payload[0].payload.ppm_privado)}/m² · ${n(payload[0].payload.n_privado)} avisos`, swatch: S[1] },
                      { label: "Abierto", value: `${usd(payload[0].payload.ppm_abierto)}/m² · ${n(payload[0].payload.n_abierto)} avisos`, swatch: S[0] },
                      { label: "Diferencial", value: `${payload[0].payload.gap_pct >= 0 ? "+" : ""}${payload[0].payload.gap_pct}%` },
                    ]}
                  />
                ) : null
              }
            />
            <Legend
              iconType="circle"
              iconSize={9}
              formatter={(v: string) => <span style={{ color: INK2, fontSize: 12 }}>{v}</span>}
            />
            <Bar name="Barrio privado" dataKey="ppm_privado" fill={S[1]} radius={[0, 4, 4, 0]} barSize={12} />
            <Bar name="Barrio abierto" dataKey="ppm_abierto" fill={S[0]} radius={[0, 4, 4, 0]} barSize={12} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ── Avisos por fuente (barras horizontales, un matiz) ───────────────────── */
export function FuenteBars({
  data,
  lastBySource = {},
}: {
  data: BreakdownRow[];
  lastBySource?: Record<string, string>;
}) {
  const NOMBRES: Record<string, string> = {
    mercadolibre: "MercadoLibre",
    remax: "RE/MAX",
    inmoclick: "Inmoclick",
    mendozaprop: "MendozaProp",
    inmoup: "InmoUp",
    argenprop: "Argenprop",
  };
  const rows = data.map((d) => ({ ...d, nombre: NOMBRES[d.grupo] || d.grupo }));
  if (!rows.length) return <Empty />;
  return (
    <div style={{ height: Math.max(140, rows.length * 36) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 40 }}>
          <CartesianGrid horizontal={false} stroke={HAIRLINE} />
          <XAxis type="number" tick={AXIS} axisLine={{ stroke: HAIRLINE }} tickLine={false} />
          <YAxis
            type="category"
            dataKey="nombre"
            width={100}
            tick={{ fill: INK2, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(122,91,208,0.07)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={String(payload[0].payload.nombre)}
                  rows={[
                    { label: "Avisos", value: n(payload[0].payload.n) },
                    { label: "Mediana", value: usd(payload[0].payload.mediana_usd) },
                    {
                      label: "Últ. dato",
                      value: fecha(lastBySource[payload[0].payload.grupo] ?? null),
                    },
                  ]}
                />
              ) : null
            }
          />
          <Bar dataKey="n" fill={S[2]} radius={[0, 4, 4, 0]} barSize={14}>
            <LabelList
              dataKey="n"
              position="right"
              formatter={(v) => n(Number(v))}
              style={{ fill: INK2, fontSize: 11, fontVariantNumeric: "tabular-nums" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Empty() {
  return (
    <div className="flex h-40 items-center justify-center text-sm text-muted">
      Sin datos para este filtro.
    </div>
  );
}
