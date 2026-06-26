"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { supabase } from "@/lib/supabase";

type Tab = "profile" | "account";

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("profile");

  // Perfil
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // Cuenta
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const u = data.user;
      if (!u) return;
      setEmail(u.email ?? "");
      setFullName((u.user_metadata?.full_name as string) ?? "");
      setPhone((u.user_metadata?.phone as string) ?? "");
    });
  }, []);

  async function saveProfile() {
    setSavingProfile(true);
    setMsg(null);
    const { error } = await supabase.auth.updateUser({ data: { full_name: fullName, phone } });
    setMsg(error ? { type: "error", text: error.message } : { type: "ok", text: "✅ Perfil actualizado." });
    setSavingProfile(false);
  }

  async function changeEmail() {
    if (!newEmail.trim()) return setMsg({ type: "error", text: "Escribe el nuevo correo." });
    setBusy(true);
    setMsg(null);
    const { error } = await supabase.auth.updateUser({ email: newEmail.trim() });
    setMsg(error
      ? { type: "error", text: error.message }
      : { type: "ok", text: "✅ Te enviamos un correo de confirmación al nuevo email. Ábrelo para aplicar el cambio." });
    setBusy(false);
    if (!error) setNewEmail("");
  }

  async function changePassword() {
    if (newPassword.length < 6) return setMsg({ type: "error", text: "La contraseña debe tener al menos 6 caracteres." });
    setBusy(true);
    setMsg(null);
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    setMsg(error ? { type: "error", text: error.message } : { type: "ok", text: "✅ Contraseña actualizada." });
    setBusy(false);
    if (!error) setNewPassword("");
  }

  return (
    <AppShell active="settings">
      <div className="page-head"><h1>Ajustes</h1></div>

      <div className="tabs">
        <div className={`tab ${tab === "profile" ? "active" : ""}`} onClick={() => setTab("profile")}>Perfil</div>
        <div className={`tab ${tab === "account" ? "active" : ""}`} onClick={() => setTab("account")}>Cuenta</div>
      </div>

      {msg && (
        <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 14, display: "block", padding: "10px 12px" }}>
          {msg.text}
        </div>
      )}

      {tab === "profile" && (
        <div className="panel" style={{ padding: 20, marginTop: 16 }}>
          <h2 style={{ fontSize: 16, margin: "0 0 4px" }}>Mi perfil</h2>
          <label>Nombre completo</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Tu nombre" />
          <label>Teléfono</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Tu número de teléfono" />
          <div style={{ marginTop: 18 }}>
            <button className="btn" onClick={saveProfile} disabled={savingProfile}>
              {savingProfile ? "Guardando…" : "Guardar cambios"}
            </button>
          </div>
        </div>
      )}

      {tab === "account" && (
        <div className="panel" style={{ padding: 20, marginTop: 16 }}>
          <h2 style={{ fontSize: 16, margin: "0 0 4px" }}>Seguridad de la cuenta</h2>

          <label>Correo actual</label>
          <div className="muted" style={{ marginBottom: 4 }}>{email || "—"}</div>
          <label>Cambiar correo</label>
          <div className="inline">
            <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="nuevo@correo.com" />
            <button className="btn secondary" onClick={changeEmail} disabled={busy} style={{ whiteSpace: "nowrap" }}>Cambiar</button>
          </div>

          <label style={{ marginTop: 22 }}>Cambiar contraseña</label>
          <div className="inline">
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Nueva contraseña (mín. 6)" />
            <button className="btn secondary" onClick={changePassword} disabled={busy} style={{ whiteSpace: "nowrap" }}>Actualizar</button>
          </div>
        </div>
      )}
    </AppShell>
  );
}
