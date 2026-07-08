"""Cliente mínimo de Google Calendar API v3 (lo que necesitan las tools).

Solo dos operaciones por ahora: consultar disponibilidad (freeBusy) y crear un
evento. Recibe un access_token ya vigente (el refresh lo maneja oauth.py).

Docs: https://developers.google.com/calendar/api/v3/reference
"""
import httpx

CAL_API = "https://www.googleapis.com/calendar/v3"


async def free_busy(access_token: str, time_min: str, time_max: str, calendar_id: str = "primary") -> list[dict]:
    """Devuelve los intervalos OCUPADOS entre time_min y time_max (ISO 8601, con tz).

    Con eso el agente deduce los huecos libres.
    """
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            f"{CAL_API}/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"timeMin": time_min, "timeMax": time_max, "items": [{"id": calendar_id}]},
        )
        resp.raise_for_status()
        cal = resp.json().get("calendars", {}).get(calendar_id, {})
        return cal.get("busy", [])


async def create_event(
    access_token: str,
    summary: str,
    start_iso: str,
    end_iso: str,
    calendar_id: str = "primary",
    description: str | None = None,
    attendee_email: str | None = None,
    time_zone: str | None = None,
) -> dict:
    """Crea un evento. start/end en ISO 8601 (con offset de tz, p.ej. -05:00)."""
    body: dict = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if time_zone:
        body["start"]["timeZone"] = time_zone
        body["end"]["timeZone"] = time_zone
    if description:
        body["description"] = description
    if attendee_email:
        body["attendees"] = [{"email": attendee_email}]

    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            f"{CAL_API}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()
