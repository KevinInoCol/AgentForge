import "./globals.css";

export const metadata = {
  title: "AgentForge",
  description: "Crea y gestiona tus agentes de texto para GoHighLevel",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
