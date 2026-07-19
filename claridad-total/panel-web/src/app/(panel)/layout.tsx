import { Sidebar } from "@/components/sidebar";

export default function PanelLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-52 px-8 py-7">{children}</main>
    </div>
  );
}
