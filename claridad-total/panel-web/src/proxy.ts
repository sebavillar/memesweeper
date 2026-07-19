import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, authDisabled, sessionToken } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  if (authDisabled()) return NextResponse.next();

  const { pathname } = request.nextUrl;
  const cookie = request.cookies.get(SESSION_COOKIE)?.value;
  const ok = cookie === (await sessionToken());

  if (pathname.startsWith("/login")) {
    // Ya logueado → al panel.
    if (ok) return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }
  if (!ok) {
    const login = new URL("/login", request.url);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  // Todo salvo assets estáticos.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg$).*)"],
};
