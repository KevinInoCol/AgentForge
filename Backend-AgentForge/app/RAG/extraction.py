"""RAG · Etapa 1 — Extracción de texto.

Convierte un archivo (PDF/TXT) en texto plano + limpieza ligera.

Parser por defecto: pypdf (local, gratis, bueno para PDFs con texto real).
Upgrade futuro: LlamaParse (mejor para tablas/multicolumna/escaneados) — requiere
el paquete `llama-parse` y `LLAMA_CLOUD_API_KEY`. Punto de extensión marcado abajo.
"""
import io
import re


def extract_text(filename: str, data: bytes) -> str:
    """Devuelve el texto limpio del archivo según su extensión."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        raw = _extract_pdf(data)
    else:  # .txt u otros de texto plano
        raw = data.decode("utf-8", errors="replace")
    return _clean(raw)


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


# --- Punto de extensión: LlamaParse (descomentar e instalar llama-parse) ------
# async def _extract_pdf_llamaparse(data: bytes) -> str:
#     from llama_parse import LlamaParse
#     parser = LlamaParse(result_type="markdown")  # usa LLAMA_CLOUD_API_KEY
#     docs = await parser.aload_data(data, extra_info={"file_name": "doc.pdf"})
#     return "\n\n".join(d.text for d in docs)


def _clean(text: str) -> str:
    """Limpieza ligera: normaliza espacios y colapsa líneas en blanco repetidas."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)          # espacios/tabs múltiples → uno
    text = re.sub(r"\n{3,}", "\n\n", text)        # 3+ saltos → doble salto
    text = re.sub(r" *\n *", "\n", text)          # espacios alrededor de saltos
    return text.strip()
