/** Formateo es-AR: 1234567 → "1.234.567". */
const nf = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });

export function n(v: number | null | undefined): string {
  return v == null ? "—" : nf.format(v);
}

export function usd(v: number | null | undefined): string {
  return v == null ? "—" : `US$ ${nf.format(v)}`;
}

/** Compacto para ejes: 85000 → "85k", 1200000 → "1,2M". */
export function compact(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace(".", ",").replace(",0", "")}M`;
  if (Math.abs(v) >= 1_000) return `${Math.round(v / 1_000)}k`;
  return String(Math.round(v));
}

export function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(+d) ? "—" : d.toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
}

/** Tiempo relativo es-AR: "hace 5 min", "hace 2 h", "ayer", "12 jul". */
export function hace(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(+d)) return "—";
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "recién";
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  if (s < 172800) return "ayer";
  if (s < 604800) return `hace ${Math.floor(s / 86400)} días`;
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
}

export const FUENTES: Record<string, string> = {
  mercadolibre: "ML",
  remax: "RE/MAX",
  inmoclick: "Inmoclick",
  mendozaprop: "MendozaProp",
  inmoup: "InmoUp",
  propio: "Propio",
};
