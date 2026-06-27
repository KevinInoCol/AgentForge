"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { supabase } from "@/lib/supabase";

type NavItem = { label: string; href: string; icon: string; key: string };

const GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Main",
    items: [
      { key: "inbox", label: "Inbox", href: "/inbox", icon: "✉️" },
      { key: "contacts", label: "Contactos", href: "/contacts", icon: "👥" },
      { key: "analisis", label: "Análisis", href: "/analisis", icon: "📊" },
    ],
  },
  {
    label: "Build",
    items: [
      { key: "assistants", label: "Asistentes", href: "/", icon: "🤖" },
      { key: "embudos", label: "Embudos", href: "/embudos", icon: "🎯" },
    ],
  },
  {
    label: "Credenciales",
    items: [
      { key: "openai", label: "Credenciales OpenAI", href: "/openai", icon: "🧠" },
      { key: "credentials", label: "Credenciales HighLevel", href: "/credentials", icon: "🔑" },
    ],
  },
  {
    label: "Deploy",
    items: [
      { key: "tags", label: "Active Tags", href: "/tags", icon: "🏷️" },
    ],
  },
];

export function AppShell({
  active,
  children,
}: {
  active: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  // Guard de sesión: sin sesión → al login.
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.replace("/login");
        return;
      }
      setEmail(data.session.user.email ?? null);
      setChecked(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      if (!session) router.replace("/login");
    });
    return () => sub.subscription.unsubscribe();
  }, [router]);

  async function logout() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!checked) {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }} className="muted">Cargando…</div>;
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/Logo-AgentForge.png" alt="AgentForge" className="brand-logo" />
        </div>

        {GROUPS.map((g) => (
          <div className="nav-group" key={g.label}>
            <div className="nav-label">{g.label}</div>
            {g.items.map((it) => (
              <a key={it.key} href={it.href} className={`nav-item ${active === it.key ? "active" : ""}`}>
                <span className="ico">{it.icon}</span>
                {it.label}
              </a>
            ))}
          </div>
        ))}

        <div className="sidebar-footer">
          <a href="/planes" className="balance" style={{ textDecoration: "none" }}>
            <span>Plan</span>
            <strong style={{ color: "#60a5fa" }}>Pro</strong>
          </a>
          <a href="/planes" className={`nav-item ${active === "planes" ? "active" : ""}`}>
            <span className="ico">💳</span>Planes
          </a>
          <a href="/settings" className="nav-item">
            <span className="ico">⚙️</span>Ajustes
          </a>
          {email && <div style={{ fontSize: 11, padding: "6px 10px 0", color: "#7c8aa3" }}>{email}</div>}
          <div className="nav-item" style={{ cursor: "pointer" }} onClick={logout}>
            <span className="ico">🚪</span>Cerrar sesión
          </div>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
