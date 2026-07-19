"use client";

import { useActionState } from "react";
import { login } from "./actions";

export default function LoginPage() {
  const [state, action, pending] = useActionState(login, null);

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        action={action}
        className="w-full max-w-sm rounded-2xl border border-hairline bg-surface p-8 shadow-sm"
      >
        <p className="font-serif text-2xl text-brand-ink">Claridad Total</p>
        <p className="mt-1 text-sm text-ink-2">
          Panel de gestión e inteligencia de mercado
        </p>
        <label className="mt-6 block text-xs font-medium uppercase tracking-wide text-muted">
          Clave de acceso
        </label>
        <input
          type="password"
          name="clave"
          autoFocus
          required
          className="mt-1.5 w-full rounded-lg border border-hairline bg-white px-3 py-2 text-sm outline-none focus:border-brand"
        />
        {state?.error && (
          <p className="mt-2 text-sm text-[#d03b3b]">{state.error}</p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="mt-5 w-full rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-ink disabled:opacity-60"
        >
          {pending ? "Verificando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
