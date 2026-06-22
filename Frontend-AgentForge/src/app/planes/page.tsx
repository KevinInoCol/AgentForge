"use client";
import { AppShell } from "@/components/AppShell";

type Plan = {
  name: string;
  price: string;
  period: string;
  tag?: string;
  highlight?: boolean;
  features: string[];
};

const PLANS: Plan[] = [
  {
    name: "Básico",
    price: "$30",
    period: "/mes",
    features: [
      "Hasta 3 agentes",
      "Base de Conocimiento (hasta 5 documentos)",
      "Canales: WhatsApp, Facebook, Instagram, SMS",
      "Lectura de texto y audios (notas de voz)",
      "Mensajes ilimitados",
      "Soporte por correo",
    ],
  },
  {
    name: "Pro",
    price: "$79",
    period: "/mes",
    tag: "Más popular",
    highlight: true,
    features: [
      "Hasta 5 agentes",
      "Base de Conocimiento (hasta 30 documentos)",
      "Tools: agendamiento, etiquetas (tags), campos personalizados",
      "Canales: WhatsApp, Facebook, Instagram, SMS",
      "Lectura de texto y audios",
      "Mensajes ilimitados",
      "Soporte prioritario",
    ],
  },
  {
    name: "Agencia",
    price: "A medida",
    period: "",
    features: [
      "Agentes ilimitados",
      "Base de Conocimiento ilimitada",
      "Todas las tools",
      "Parseo avanzado de PDF (tablas / escaneados)",
      "Soporte dedicado",
    ],
  },
];

export default function PlanesPage() {
  return (
    <AppShell active="planes">
      <div className="page-head">
        <h1>Planes</h1>
      </div>

      <p className="muted" style={{ maxWidth: 640 }}>
        Elige el plan según cuántos agentes y qué capacidades necesites. Todos los planes
        usan <strong>tu propia API key de OpenAI</strong> (el consumo de tokens se cobra a tu
        cuenta de OpenAI, no va incluido en el plan).
      </p>

      <div className="plans-grid">
        {PLANS.map((p) => (
          <div key={p.name} className={`plan-card ${p.highlight ? "highlight" : ""}`}>
            {p.tag && <span className="plan-tag">{p.tag}</span>}
            <div className="plan-name">{p.name}</div>
            <div className="plan-price">
              {p.price}
              {p.period && <small>{p.period}</small>}
            </div>
            <ul className="plan-features">
              {p.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <button className={`btn ${p.highlight ? "" : "secondary"}`} style={{ marginTop: 18, justifyContent: "center" }} disabled>
              {p.price === "A medida" ? "Contactar" : "Próximamente"}
            </button>
          </div>
        ))}
      </div>

      <p className="muted" style={{ marginTop: 18, fontSize: 12 }}>
        El cobro automático se habilitará pronto. Por ahora los planes se asignan manualmente.
      </p>
    </AppShell>
  );
}
