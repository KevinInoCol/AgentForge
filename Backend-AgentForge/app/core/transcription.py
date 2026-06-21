"""Transcripción de notas de voz (audio → texto) con OpenAI Whisper.

Se usa cuando entra un mensaje de audio (WhatsApp/Facebook). Descarga el archivo
desde la URL del adjunto y lo transcribe con la API de OpenAI del cliente, para
que el agente lo procese como si fuera texto.
"""
import logging

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def transcribe_audio(url: str, api_key: str) -> str:
    """Descarga el audio de `url` y devuelve su transcripción en texto."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        audio_bytes = resp.content

    filename = url.split("?")[0].rsplit("/", 1)[-1] or "audio.ogg"
    client = AsyncOpenAI(api_key=api_key)
    result = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes),
    )
    text = (result.text or "").strip()
    logger.warning("[turn] 🎙️ audio transcrito: %r", text[:120])
    return text
