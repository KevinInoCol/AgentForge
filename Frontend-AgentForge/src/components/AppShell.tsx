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
    ],
  },
  {
    label: "Build",
    items: [
      { key: "assistants", label: "Asistentes", href: "/", icon: "🤖" },
      { key: "widgets", label: "Widgets", href: "/widgets", icon: "🔲" },
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
      { key: "integrations", label: "Integraciones", href: "/integrations", icon: "🔌" },
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
          <div className="mark">A</div>
          <div className="name">AgentForge</div>
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
          <div className="balance">
            <span>Balance</span>
            <strong>$0.00</strong>
          </div>
          <a href="/settings" className="nav-item">
            <span className="ico">⚙️</span>Ajustes
          </a>
          {email && <div className="muted" style={{ fontSize: 11, padding: "6px 10px 0" }}>{email}</div>}
          <div className="nav-item" style={{ cursor: "pointer" }} onClick={logout}>
            <span className="ico">🚪</span>Cerrar sesión
          </div>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
