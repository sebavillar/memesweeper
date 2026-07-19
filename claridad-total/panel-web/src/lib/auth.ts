/** Autenticación simple por contraseña única (la misma PANEL_PASSWORD del bot).
 *  La sesión es una cookie httpOnly cuyo valor es un hash derivado de la clave;
 *  usa Web Crypto para funcionar igual en Node y en el runtime del proxy. */

export const SESSION_COOKIE = "ct_session";

export async function sessionToken(): Promise<string> {
  const secret = process.env.PANEL_PASSWORD || "";
  const data = new TextEncoder().encode(`claridad-total-panel:${secret}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function authDisabled(): boolean {
  return !process.env.PANEL_PASSWORD;
}
