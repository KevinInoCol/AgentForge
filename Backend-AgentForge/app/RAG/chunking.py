"""RAG · Etapa 2 — Chunking (troceado).

Divide el texto en fragmentos respetando la estructura (párrafos, líneas).
Parámetros decididos por la plataforma (el usuario no los toca). Para afinar la
calidad, ajustar aquí en un solo lugar.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


def chunk_text(text: str) -> list[str]:
    return _splitter.split_text(text)
