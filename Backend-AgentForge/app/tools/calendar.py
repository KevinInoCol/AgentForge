"""Tools de Google Calendar, ligadas a la conexión OAuth del tenant.

Cada tool descifra las credenciales de la conexión, obtiene un access_token
vigente (refrescándolo y re-guardándolo si expiró) y llama a la Calendar API.
Como toda tool del runtime, falla SUAVE: ante error devuelve texto, no excepción,
para no tumbar el turno.
"""
import logging

from langchain_core.tools import StructuredTool

from app.core.crypto import decrypt_json, encrypt_json
from app.db.queries import update_connection
from app.integrations.google import calendar as gcal
from app.integrations.google.oauth import valid_access_token

logger = logging.getLogger(__name__)


def get_calendar_tools(connection: dict) -> list[StructuredTool]:
    """Devuelve las tools de calendario ligadas a ESTA conexión del workspace."""
    conn_id = connection["id"]
    calendar_id = (connection.get("config") or {}).get("calendar_id", "primary")
    time_zone = (connection.get("config") or {}).get("time_zone")

    async def _access_token() -> str:
        """Token vigente; si se refrescó, re-cifra y persiste las credenciales."""
        creds = decrypt_json(connection["credentials"])
        token, used = await valid_access_token(creds)
        if used is not creds:  # hubo refresh → guardar el nuevo access_token
            connection["credentials"] = encrypt_json(used)
            await update_connection(conn_id, {"credentials": connection["credentials"]})
        return token

    async def consultar_disponibilidad(desde_iso: str, hasta_iso: str) -> str:
        """Consulta los horarios ocupados en el calendario entre dos fechas."""
        try:
            token = await _access_token()
            busy = await gcal.free_busy(token, desde_iso, hasta_iso, calendar_id)
        except Exception:  # noqa: BLE001
            logger.exception("[calendar] error consultando disponibilidad")
            return "No se pudo consultar la disponibilidad en este momento."
        if not busy:
            return f"No hay horarios ocupados entre {desde_iso} y {hasta_iso}: todo libre."
        bloques = "; ".join(f"{b['start']} → {b['end']}" for b in busy)
        return f"Horarios OCUPADOS (el resto está libre): {bloques}"

    async def crear_evento(
        titulo: str,
        inicio_iso: str,
        fin_iso: str,
        email_invitado: str | None = None,
        descripcion: str | None = None,
    ) -> str:
        """Crea un evento/cita en el calendario."""
        try:
            token = await _access_token()
            ev = await gcal.create_event(
                token, titulo, inicio_iso, fin_iso, calendar_id,
                description=descripcion, attendee_email=email_invitado, time_zone=time_zone,
            )
        except Exception:  # noqa: BLE001
            logger.exception("[calendar] error creando evento")
            return "No se pudo crear el evento en este momento."
        link = ev.get("htmlLink", "")
        return f"Evento '{titulo}' creado para {inicio_iso}." + (f" Link: {link}" if link else "")

    return [
        StructuredTool.from_function(
            coroutine=consultar_disponibilidad,
            name="consultar_disponibilidad",
            description=(
                "Consulta la disponibilidad en el calendario de Google entre dos fechas. "
                "Pasa 'desde_iso' y 'hasta_iso' en formato ISO 8601 con zona horaria "
                "(ej. 2026-07-10T09:00:00-05:00). Úsala ANTES de agendar para ofrecer horarios libres."
            ),
        ),
        StructuredTool.from_function(
            coroutine=crear_evento,
            name="crear_evento",
            description=(
                "Crea una cita/evento en el calendario de Google. 'inicio_iso' y 'fin_iso' "
                "en ISO 8601 con zona horaria. Confirma con el contacto fecha y hora antes de crear. "
                "Opcional: 'email_invitado' para enviarle la invitación."
            ),
        ),
    ]
