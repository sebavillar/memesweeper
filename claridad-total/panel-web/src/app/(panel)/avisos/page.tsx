export const dynamic = "force-dynamic";

import Link from "next/link";
import { api, qsMercado, type Filtros, type Listings } from "@/lib/api";
import { FilterBar } from "@/components/filter-bar";
import { Card, SourcePill } from "@/components/ui";
import { fecha, n, usd } from "@/lib/format";

const SORTS: { key: string; label: string }[] = [
  { key: "-fetched_at", label: "Más recientes" },
  { key: "-precio_usd", label: "Mayor precio" },
  { key: "precio_usd", label: "Menor precio" },
  { key: "-ppm", label: "Mayor USD/m²" },
  { key: "ppm", label: "Menor USD/m²" },
];

export default async function AvisosPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const page = Number(sp.page) || 1;
  const sort = typeof sp.sort === "string" ? sp.sort : "-fetched_at";
  const qs = qsMercado(sp);
  const amp = qs ? `&${qs}` : "";

  const [filtros, listings] = await Promise.all([
    api<Filtros>("/api/v1/market/filters"),
    api<Listings>(
      `/api/v1/market/listings?page=${page}&page_size=25&sort=${encodeURIComponent(sort)}${amp}`,
    ),
  ]);

  const pages = Math.max(1, Math.ceil(listings.total / listings.page_size));
  const qsBase = new URLSearchParams(qs);
  qsBase.set("sort", sort);
  const hrefPage = (p: number) => {
    const u = new URLSearchParams(qsBase);
    u.set("page", String(p));
    return `/avisos?${u.toString()}`;
  };
  const hrefSort = (s: string) => {
    const u = new URLSearchParams(qs);
    u.set("sort", s);
    return `/avisos?${u.toString()}`;
  };

  return (
    <>
      <header className="mb-5">
        <h1 className="font-serif text-2xl text-ink">Avisos relevados</h1>
        <p className="mt-0.5 text-sm text-ink-2">
          {n(listings.total)} avisos en venta con el filtro actual
        </p>
      </header>

      <FilterBar filtros={filtros} />

      <div className="mt-4 flex flex-wrap gap-1.5">
        {SORTS.map((s) => (
          <Link
            key={s.key}
            href={hrefSort(s.key)}
            className={`rounded-full px-3 py-1 text-xs transition-colors ${
              s.key === sort
                ? "bg-brand text-white"
                : "border border-hairline bg-surface text-ink-2 hover:text-ink"
            }`}
          >
            {s.label}
          </Link>
        ))}
      </div>

      <Card className="mt-4 overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-hairline text-left text-[11px] uppercase tracking-wide text-muted">
              <th className="px-4 py-3 font-medium">Aviso</th>
              <th className="px-3 py-3 font-medium">Fuente</th>
              <th className="px-3 py-3 font-medium">Tipo</th>
              <th className="px-3 py-3 font-medium">Departamento</th>
              <th className="px-3 py-3 text-right font-medium">Precio</th>
              <th className="px-3 py-3 text-right font-medium">m²</th>
              <th className="px-3 py-3 text-right font-medium">USD/m²</th>
              <th className="px-3 py-3 text-right font-medium">Dorm.</th>
              <th className="px-3 py-3 text-right font-medium">Antig.</th>
              <th className="px-4 py-3 text-right font-medium">Visto</th>
            </tr>
          </thead>
          <tbody>
            {listings.rows.map((r) => (
              <tr
                key={`${r.source}-${r.listing_id}`}
                className="border-b border-hairline last:border-0 hover:bg-page/60"
              >
                <td className="max-w-72 truncate px-4 py-2.5">
                  {r.url ? (
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noopener"
                      className="text-brand-ink hover:underline"
                    >
                      {r.titulo || r.listing_id}
                    </a>
                  ) : (
                    r.titulo || r.listing_id
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <SourcePill source={r.source} />
                </td>
                <td className="px-3 py-2.5 capitalize text-ink-2">{r.tipo || "—"}</td>
                <td className="px-3 py-2.5 text-ink-2">{r.depto_norm || "—"}</td>
                <td className="tnum px-3 py-2.5 text-right">{usd(r.precio_usd)}</td>
                <td className="tnum px-3 py-2.5 text-right text-ink-2">
                  {n(r.m2_cubierta || r.m2_total)}
                </td>
                <td className="tnum px-3 py-2.5 text-right text-ink-2">{n(r.ppm)}</td>
                <td className="tnum px-3 py-2.5 text-right text-ink-2">
                  {r.dormitorios ?? "—"}
                </td>
                <td className="tnum px-3 py-2.5 text-right text-ink-2">
                  {r.antiguedad == null
                    ? "—"
                    : r.antiguedad === 0
                      ? "a estrenar"
                      : `${r.antiguedad} a`}
                </td>
                <td className="tnum px-4 py-2.5 text-right text-ink-2">
                  {fecha(r.fetched_at)}
                </td>
              </tr>
            ))}
            {!listings.rows.length && (
              <tr>
                <td colSpan={10} className="px-4 py-10 text-center text-muted">
                  Sin avisos para este filtro.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      {pages > 1 && (
        <nav className="mt-4 flex items-center justify-between text-sm">
          <p className="text-muted">
            Página {page} de {pages}
          </p>
          <div className="flex gap-2">
            {page > 1 && (
              <Link
                href={hrefPage(page - 1)}
                className="rounded-lg border border-hairline bg-surface px-3 py-1.5 text-ink-2 hover:text-ink"
              >
                ← Anterior
              </Link>
            )}
            {page < pages && (
              <Link
                href={hrefPage(page + 1)}
                className="rounded-lg border border-hairline bg-surface px-3 py-1.5 text-ink-2 hover:text-ink"
              >
                Siguiente →
              </Link>
            )}
          </div>
        </nav>
      )}
    </>
  );
}
