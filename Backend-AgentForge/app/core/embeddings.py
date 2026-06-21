"""Embeddings con OpenAI (usando la API key del cliente).

text-embedding-3-small → 1536 dimensiones (coincide con la columna vector(1536)).
"""
from openai import AsyncOpenAI

EMBED_MODEL = "text-embedding-3-small"


async def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


async def embed_query(text: str, api_key: str) -> list[float]:
    return (await embed_texts([text], api_key))[0]
