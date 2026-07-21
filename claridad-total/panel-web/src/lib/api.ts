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
  privados: number;
  fuentes_last: Record<string, string>;
  total: number;
  last_fetch: string | null;
};

export type AgeData = {
  points: { edad: number; ppm: number; tipo: string | null; depto: string | null }[];
  bandas: { banda: string; edad: number; n: number; ppm: number }[];
  n: number;
};

export type PrivadoGapSide = {
  ppm_privado: number | null;
  ppm_abierto: number | null;
  n_privado: number;
  n_abierto: number;
  gap_pct: number | null;
};

export type PrivadoGap = {
  global: PrivadoGapSide;
  por_depto: (PrivadoGapSide & { grupo: string })[];
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
  antiguedad: number | null;
  barrio_privado: number | null;
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

export type Actividad = {
  dias: {
    fecha: string;
    nuevos: number;
    por_fuente: Record<string, number>;
    cambios_precio: number;
    vistos: number;
  }[];
};

export type LeadMsg = { role: "user" | "assistant"; text: string };

export type Lead = {
  wa_id: string;
  nombre: string | null;
  telefono: string | null;
  wa_link: string | null;
  temperatura: "caliente" | "tibio" | "frio";
  score: number;
  presupuesto_usd: number | null;
  zona: string | null;
  tipo: string | null;
  ambientes: number | null;
  urgencia: string | null;
  necesita_credito: boolean | null;
  handoff: boolean;
  handoff_motivo: string | null;
  visita_agendada: boolean;
  mensajes: number;
  creado: string | null;
  actualizado: string | null;
  ultimo_mensaje: LeadMsg | null;
};

export type LeadSummary = {
  total: number;
  calientes: number;
  tibios: number;
  handoffs: number;
  con_visita: number;
  visitas: number;
};

export type Visita = {
  wa_id?: string;
  propiedad?: string;
  propiedad_id?: string;
  fecha_hora?: string;
  nombre?: string | null;
  telefono?: string | null;
  creada?: string;
};

export type LeadDetail = {
  lead: Lead;
  conversacion: LeadMsg[];
  visitas: Visita[];
};

/** Convierte los searchParams del dashboard en querystring para la API. */
export function qsMercado(sp: Record<string, string | string[] | undefined>): string {
  const p = new URLSearchParams();
  for (const k of ["depto", "tipo", "fuente", "usd_min", "usd_max", "m2_min", "m2_max", "privado"]) {
    const v = sp[k];
    if (typeof v === "string" && v) p.set(k, v);
  }
  return p.toString();
}
