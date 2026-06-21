"use client";
import { useEffect, useState } from "react";

import { getMyWorkspace } from "@/lib/api";

/**
 * Devuelve el id del workspace del usuario autenticado (lo crea si no tiene).
 * Estados: `undefined` = cargando · `string` = listo · `null` = error/sin sesión.
 */
export function useWorkspaceId(): string | null | undefined {
  const [id, setId] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    getMyWorkspace()
      .then((w) => setId(w.id))
      .catch(() => setId(null));
  }, []);

  return id;
}
