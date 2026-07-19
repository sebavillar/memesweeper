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

export const FUENTES: Record<string, string> = {
  mercadolibre: "ML",
  remax: "RE/MAX",
  inmoclick: "Inmoclick",
  propio: "Propio",
};
