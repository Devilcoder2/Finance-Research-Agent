import os
import uuid
import hashlib
from typing import List, Optional
# pyrefly: ignore [missing-import]
from langchain_google_genai import GoogleGenerativeAIEmbeddings
# pyrefly: ignore [missing-import]
from sqlalchemy import select
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.models import LongTermMemory

def get_embeddings_model() -> Optional[GoogleGenerativeAIEmbeddings]:
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key:
        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_key
        )
    return None

async def embed_text(text: str) -> List[float]:
    model = get_embeddings_model()
    if model:
        try:
            return await model.aembed_query(text)
        except Exception as e:
            print(f"Error generating embedding via API: {e}. Falling back to mock vector.")
    
    # Mock fallback (768 dimensions)
    # Seed a deterministic vector based on the hash of the text so that similarity can be tested
    h = hashlib.sha256(text.encode("utf-8")).digest()
    mock_vec = []
    for i in range(768):
        byte_val = h[i % len(h)]
        mock_vec.append((byte_val / 127.5) - 1.0)
    return mock_vec

async def save_memory(db: AsyncSession, user_id: uuid.UUID, ticker: str, section_id: str, comment: str) -> LongTermMemory:
    memory_text = f"Analyst preference for {ticker.upper()} ({section_id}): {comment}"
    embedding = await embed_text(memory_text)
    
    db_memory = LongTermMemory(
        user_id=user_id,
        ticker=ticker.upper(),
        embedding=embedding,
        memory_text=memory_text
    )
    db.add(db_memory)
    await db.commit()
    return db_memory

async def search_memories(db: AsyncSession, user_id: uuid.UUID, tickers: List[str], limit: int = 5) -> List[str]:
    """
    Search for relevant long-term memories for a list of tickers.
    Filters by user_id and tickers, ordering by semantic similarity to a prompt.
    """
    if not tickers:
        return []
    
    query_text = f"Investment preferences and feedback for {', '.join(tickers)}"
    query_embedding = await embed_text(query_text)
    
    tickers_upper = [t.upper() for t in tickers]
    stmt = (
        select(LongTermMemory.memory_text)
        .where(LongTermMemory.user_id == user_id)
        .where(LongTermMemory.ticker.in_(tickers_upper))
        .order_by(LongTermMemory.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
