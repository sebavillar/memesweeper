import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Claridad Total · Panel",
  description: "Panel de gestión e inteligencia de mercado inmobiliario",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
