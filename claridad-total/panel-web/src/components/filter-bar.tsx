"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import type { Filtros } from "@/lib/api";

/** Fila única de filtros sobre los gráficos. Cada cambio actualiza la URL
 *  (?depto=…&tipo=…) y el servidor re-renderiza con los datos filtrados. */
export function FilterBar({ filtros }: { filtros: Filtros }) {
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  const [pending, start] = useTransition();

  function setParam(k: string, v: string) {
    const p = new URLSearchParams(sp.toString());
    if (v) p.set(k, v);
    else p.delete(k);
    p.delete("page"); // los filtros resetean la paginación
    start(() => router.push(`${path}?${p.toString()}`));
  }

  const sel =
    "rounded-lg border border-hairline bg-surface px-2.5 py-1.5 text-sm text-ink outline-none focus:border-brand";

  return (
    <div
      className={`flex flex-wrap items-center gap-2 transition-opacity ${
        pending ? "opacity-60" : ""
      }`}
    >
      <select
        aria-label="Departamento"
        className={sel}
        value={sp.get("depto") || ""}
        onChange={(e) => setParam("depto", e.target.value)}
      >
        <option value="">Todos los departamentos</option>
        {filtros.departamentos.map((d) => (
          <option key={d.nombre} value={d.nombre}>
            {d.nombre} ({d.n})
          </option>
        ))}
      </select>

      <select
        aria-label="Tipo"
        className={sel}
        value={sp.get("tipo") || ""}
        onChange={(e) => setParam("tipo", e.target.value)}
      >
        <option value="">Todos los tipos</option>
        {filtros.tipos.map((t) => (
          <option key={t.nombre} value={t.nombre} className="capitalize">
            {t.nombre} ({t.n})
          </option>
        ))}
      </select>

      <select
        aria-label="Fuente"
        className={sel}
        value={sp.get("fuente") || ""}
        onChange={(e) => setParam("fuente", e.target.value)}
      >
        <option value="">Todas las fuentes</option>
        {filtros.fuentes.map((f) => (
          <option key={f.nombre} value={f.nombre}>
            {f.nombre} ({f.n})
          </option>
        ))}
      </select>

      <div className="flex items-center gap-1.5">
        <input
          aria-label="Precio mínimo USD"
          type="number"
          placeholder="USD mín"
          defaultValue={sp.get("usd_min") || ""}
          onBlur={(e) => setParam("usd_min", e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && setParam("usd_min", e.currentTarget.value)
          }
          className={`${sel} w-28`}
        />
        <span className="text-muted">–</span>
        <input
          aria-label="Precio máximo USD"
          type="number"
          placeholder="USD máx"
          defaultValue={sp.get("usd_max") || ""}
          onBlur={(e) => setParam("usd_max", e.target.value)}
          onKeyDown={(e) =>
            e.key === "Enter" && setParam("usd_max", e.currentTarget.value)
          }
          className={`${sel} w-28`}
        />
      </div>

      {sp.size > 0 && (
        <button
          onClick={() => start(() => router.push(path))}
          className="rounded-lg px-2.5 py-1.5 text-sm text-brand-ink hover:bg-brand/10"
        >
          Limpiar
        </button>
      )}
    </div>
  );
}
