/** Cliente server-side de la API del bot (FastAPI). Corre solo en el servidor:
 *  la clave nunca llega al navegador. */

const BASE = process.env.BACKEND_URL || "http://localhost:8080";
const AUTH =
  "Basic " +
  Buffer.from(`panel:${process.env.PANEL_PASSWORD || ""}`).toString("base64");

export async function api<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { Authorization: AUTH },
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`API ${r.status} en ${path}`);
  return r.json() as Promise<T>;
}

/* ── Tipos de la API ─────────────────────────────────────────────────────── */

export type Filtros = {
  departamentos: { nombre: string; n: number }[];
  tipos: { nombre: string; n: number }[];
  fuentes: { nombre: string; n: number }[];
  total: number;
  last_fetch: string | null;
};

export type Summary = {
  n: number;
  mediana_usd: number | null;
  ppm_mediano: number | null;
  ppm_p25: number | null;
  ppm_p75: number | null;
  con_m2: number;
};

export type BreakdownRow = Summary & { grupo: string };

export type Histogram = {
  buckets: { desde: number; hasta: number; n: number }[];
  recortados: number;
};

export type ScatterPoint = {
  m2: number;
  usd: number;
  tipo: string | null;
  depto: string | null;
  fuente: string;
};

export type ListingRow = {
  source: string;
  listing_id: string;
  titulo: string | null;
  url: string | null;
  tipo: string | null;
  precio_usd: number | null;
  m2_cubierta: number | null;
  m2_total: number | null;
  ppm: number | null;
  dormitorios: number | null;
  depto_norm: string | null;
  fetched_at: string | null;
};

export type Listings = {
  total: number;
  page: number;
  page_size: number;
  rows: ListingRow[];
};

export type Prop = {
  id: string;
  titulo?: string;
  tipo?: string;
  estado?: string;
  precio_usd?: number;
  departamento?: string;
  barrio?: string;
  direccion?: string;
  ambientes?: number;
  dormitorios?: number;
  banos?: number;
  sup_cubierta?: number;
  sup_total?: number;
  antiguedad?: number;
  cochera?: boolean;
  caracteristicas?: string[];
  descripcion?: string;
  fotos?: string[];
  stats?: Record<string, number>;
};

export type Valuacion = {
  valor: number;
  low: number;
  high: number;
  oferta_sugerida: number;
  ppm: number;
  confianza: number;
  n_comparables: number;
  zona_m2: number;
  factores: { label: string; detalle: string; val: number }[];
  comparables: {
    id: string;
    titulo: string;
    precio_usd: number;
    ppm: number;
    estado: string;
    source: string;
    url: string | null;
  }[];
  fuentes: Record<string, string>;
};

/** Convierte los searchParams del dashboard en querystring para la API. */
export function qsMercado(sp: Record<string, string | string[] | undefined>): string {
  const p = new URLSearchParams();
  for (const k of ["depto", "tipo", "fuente", "usd_min", "usd_max", "m2_min", "m2_max"]) {
    const v = sp[k];
    if (typeof v === "string" && v) p.set(k, v);
  }
  return p.toString();
}
