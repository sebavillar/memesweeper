import { FUENTES } from "@/lib/format";

/** Tarjeta base del panel. */
export function Card({
  title,
  subtitle,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-hairline bg-surface p-5 ${className}`}
    >
      {title && (
        <header className="mb-4">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

/** Tile de indicador (número protagonista). */
export function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-hairline bg-surface px-5 py-4">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">
        {label}
      </p>
      <p className="mt-1 text-[26px] font-semibold leading-tight text-ink">
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs text-ink-2">{hint}</p>}
    </div>
  );
}

const PILL_STYLE: Record<string, string> = {
  mercadolibre: "bg-[#9C6A15]/10 text-[#7a5410]",
  remax: "bg-[#0993ab]/10 text-[#076c7c]",
  inmoclick: "bg-[#7a5bd0]/10 text-[#5b41a8]",
  propio: "bg-[#d54f74]/10 text-[#a83b58]",
};

/** Etiqueta de fuente (ML / RE/MAX / Inmoclick / Propio). */
export function SourcePill({ source }: { source: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ${
        PILL_STYLE[source] || "bg-page text-ink-2"
      }`}
    >
      {FUENTES[source] || source}
    </span>
  );
}

export function EstadoPill({ estado }: { estado?: string }) {
  const map: Record<string, string> = {
    disponible: "bg-[#0ca30c]/10 text-[#006300]",
    reservada: "bg-[#9C6A15]/10 text-[#7a5410]",
    vendida: "bg-page text-muted",
  };
  const e = estado || "—";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${
        map[e] || "bg-page text-ink-2"
      }`}
    >
      {e}
    </span>
  );
}
