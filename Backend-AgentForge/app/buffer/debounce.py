"""Buffer + debounce con Redis para concatenar mensajes seguidos.

Patrón (skill message-concatenation-buffer): por cada mensaje hacemos RPUSH a una
lista y INCR de un contador de secuencia; programamos una tarea que espera la
ventana de silencio y SOLO procesa si su secuencia sigue siendo la última. Así
"gana" el último mensaje y nunca hay respuestas duplicadas.

Para el MVP las tareas corren en el mismo proceso FastAPI (asyncio). Cuando
escalemos, esto se mueve a una cola + workers (app/workers/).
"""
import asyncio
import logging
from typing import Awaitable, Callable

from app.buffer.redis_client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)

# Mantener referencias fuertes para que el GC no cancele las tareas.
_tasks: set[asyncio.Task] = set()

ProcessCallback = Callable[[str], Awaitable[None]]


def _msgs_key(buffer_id: str) -> str:
    return f"agentforge:buffer:msgs:{buffer_id}"


def _seq_key(buffer_id: str) -> str:
    return f"agentforge:buffer:seq:{buffer_id}"


async def enqueue_message(buffer_id: str, text: str, process: ProcessCallback) -> None:
    """Acumula `text` y programa el flush. `process(concatenado)` se llama una vez.

    Si el buffer está deshabilitado O Redis no está disponible, responde directo
    (mensaje por mensaje) en vez de fallar. Así el debounce es opcional.
    """
    if not settings.buffer_enabled:
        await process(text)
        return

    try:
        r = get_redis()
        msgs_key, seq_key = _msgs_key(buffer_id), _seq_key(buffer_id)

        await r.rpush(msgs_key, text)
        my_seq = await r.incr(seq_key)
        await r.expire(msgs_key, settings.buffer_ttl_seconds)
        await r.expire(seq_key, settings.buffer_ttl_seconds)

        task = asyncio.create_task(_wait_and_process(buffer_id, my_seq, process))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    except Exception:  # noqa: BLE001 — Redis caído no debe romper la respuesta
        logger.warning("Redis no disponible; respondiendo sin debounce", exc_info=False)
        await process(text)


async def _wait_and_process(buffer_id: str, my_seq: int, process: ProcessCallback) -> None:
    r = get_redis()
    msgs_key, seq_key = _msgs_key(buffer_id), _seq_key(buffer_id)

    await asyncio.sleep(settings.buffer_window_seconds)

    current = await r.get(seq_key)
    if current is None or int(current) != my_seq:
        return  # llegó un mensaje más nuevo; esa tarea se encarga

    messages = await r.lrange(msgs_key, 0, -1)
    if not messages:
        return

    combined = settings.buffer_separator.join(messages)
    n = len(messages)
    try:
        await process(combined)
    finally:
        # Limpiar SIEMPRE tras responder (a prueba de carreras).
        final = await r.get(seq_key)
        if final is not None and int(final) == my_seq:
            await r.delete(msgs_key, seq_key)        # nada nuevo → borrar todo
        else:
            await r.ltrim(msgs_key, n, -1)           # llegaron nuevos → conservar
