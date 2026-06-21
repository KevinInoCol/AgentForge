"""RAG · Etapa 3 — Embeddings (texto → vectores) con OpenAI.

Modelo: text-embedding-3-large, truncado a 1536 dims (parámetro `dimensions`)
para mantener la columna vector(1536) y el índice ivfflat (límite 2000 dims).
3-large@1536 tiene mejor calidad que 3-small@1536.

Usa la API key del cliente (cada uno paga su consumo).
"""
from openai import AsyncOpenAI

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMENSIONS = 1536


async def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        dimensions=EMBED_DIMENSIONS,
    )
    return [d.embedding for d in resp.data]


async def embed_query(text: str, api_key: str) -> list[float]:
    return (await embed_texts([text], api_key))[0]
