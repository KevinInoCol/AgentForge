"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Si ya hay sesión, entra directo.
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/");
    });
  }, [router]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    if (error) {
      setError("Correo o contraseña incorrectos.");
      setLoading(false);
      return;
    }
    router.replace("/");
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <form onSubmit={handleLogin} className="panel" style={{ width: "100%", maxWidth: 380, padding: 28 }}>
        <div className="brand" style={{ padding: "0 0 18px" }}>
          <div className="mark">A</div>
          <div className="name">AgentForge</div>
        </div>
        <h1 style={{ fontSize: 18, marginBottom: 2 }}>Inicia sesión</h1>
        <p className="muted" style={{ marginTop: 0 }}>Entra con tu cuenta para gestionar tus agentes.</p>

        <label>Correo</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.com" required autoFocus />

        <label>Contraseña</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />

        {error && <div className="error">{error}</div>}

        <button className="btn" type="submit" disabled={loading} style={{ width: "100%", marginTop: 20, justifyContent: "center" }}>
          {loading ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
