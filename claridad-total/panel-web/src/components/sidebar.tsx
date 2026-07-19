"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/app/login/actions";

const NAV = [
  { href: "/", label: "Mercado", icon: "◧" },
  { href: "/avisos", label: "Avisos", icon: "☰" },
  { href: "/inventario", label: "Inventario", icon: "⌂" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-52 flex-col border-r border-hairline bg-surface">
      <div className="px-5 pb-4 pt-6">
        <p className="font-serif text-lg leading-tight text-brand-ink">
          Claridad Total
        </p>
        <p className="text-[11px] uppercase tracking-widest text-muted">
          Panel inmobiliario
        </p>
      </div>
      <nav className="flex-1 space-y-0.5 px-3">
        {NAV.map((it) => {
          const active =
            it.href === "/" ? path === "/" : path.startsWith(it.href);
          return (
            <Link
              key={it.href}
              href={it.href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-brand/10 font-medium text-brand-ink"
                  : "text-ink-2 hover:bg-page hover:text-ink"
              }`}
            >
              <span aria-hidden className="text-base leading-none">
                {it.icon}
              </span>
              {it.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-hairline p-3">
        <form action={logout}>
          <button
            type="submit"
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted transition-colors hover:bg-page hover:text-ink"
          >
            Cerrar sesión
          </button>
        </form>
      </div>
    </aside>
  );
}
