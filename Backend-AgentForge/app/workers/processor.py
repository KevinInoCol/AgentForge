"""Workers para la FASE DE ESCALA (no se usa en el MVP).

En el MVP, el debounce (app/buffer/debounce.py) corre las tareas como asyncio
dentro del mismo proceso FastAPI. Eso es suficiente para empezar.

Cuando el volumen crezca, mover el procesamiento aquí: el webhook encola un job
en Redis/cola y N réplicas de este worker consumen y llaman a
app.core.runtime.process_turn. Así el web y el cómputo escalan por separado.
"""
