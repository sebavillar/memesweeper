export const dynamic = "force-dynamic";

import Link from "next/link";
import { api, type Prop } from "@/lib/api";
import { Card, EstadoPill } from "@/components/ui";
import { n, usd } from "@/lib/format";

export default async function InventarioPage() {
  const props = await api<Prop[]>("/api/v1/inventory");
  const disponibles = props.filter((p) => p.estado === "disponible").length;

  return (
    <>
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-2xl text-ink">Inventario</h1>
          <p className="mt-0.5 text-sm text-ink-2">
            {props.length} propiedades · {disponibles} disponibles
          </p>
        </div>
        <a
          href="/panel/inventario"
          className="rounded-lg border border-hairline bg-surface px-3 py-1.5 text-sm text-ink-2 hover:text-ink"
          title="Alta y edición (panel clásico)"
        >
          ✏️ Cargar / editar
        </a>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {props.map((p) => (
          <Link key={p.id} href={`/inventario/${p.id}`} className="group">
            <Card className="h-full transition-shadow group-hover:shadow-md">
              <div className="-m-5 mb-4 h-40 overflow-hidden rounded-t-2xl bg-page">
                {p.fotos?.[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={p.fotos[0]}
                    alt=""
                    className="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-3xl text-muted">
                    ⌂
                  </div>
                )}
              </div>
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium leading-snug text-ink">{p.titulo}</p>
                <EstadoPill estado={p.estado} />
              </div>
              <p className="mt-0.5 text-xs text-muted">
                {[p.barrio, p.departamento].filter(Boolean).join(" · ")}
              </p>
              <p className="tnum mt-2 text-lg font-semibold text-brand-ink">
                {usd(p.precio_usd)}
              </p>
              <p className="mt-1 text-xs text-ink-2">
                {[
                  p.sup_cubierta && `${n(p.sup_cubierta)} m²`,
                  p.ambientes && `${p.ambientes} amb`,
                  p.dormitorios && `${p.dormitorios} dorm`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {p.stats && Object.keys(p.stats).length > 0 && (
                <p className="mt-2 text-xs text-muted">
                  {[
                    p.stats.ofrecida && `${p.stats.ofrecida}× ofrecida`,
                    p.stats.ficha && `${p.stats.ficha} fichas`,
                    p.stats.visitas && `${p.stats.visitas} visitas`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </>
  );
}
