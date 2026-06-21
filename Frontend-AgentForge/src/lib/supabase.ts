import { createClient } from "@supabase/supabase-js";

// Fallback a placeholder para que el build/prerender no truene si faltan las env.
// En runtime (navegador) deben estar NEXT_PUBLIC_SUPABASE_URL/ANON_KEY reales.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "https://placeholder.supabase.co";
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "placeholder-anon-key";

export const supabase = createClient(url, anonKey);
