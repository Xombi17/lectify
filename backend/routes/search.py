"""Semantic + lexical search across published lectures."""
import math
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from core.deps import get_current_user
from models.chat import SearchResult
from models.user import UserPublic
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service

router = APIRouter(tags=["search"])


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _lexical_score(text: str, query: str) -> float:
    text_l = (text or "").lower()
    tokens = [t for t in re.split(r"\W+", query.lower()) if t]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in text_l)
    return hits / len(tokens)


@router.get("/search", response_model=List[SearchResult])
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(8, ge=1, le=25),
    user: UserPublic = Depends(get_current_user),
):
    lec_repo = LectureRepository()
    docs = await lec_repo.list_published_embeddings()
    if not docs:
        return []

    query_embedding: list[float] | None = None
    try:
        query_embedding = await get_ai_service().embed(q)
    except Exception:
        query_embedding = None  # falls back to lexical scoring

    results: list[SearchResult] = []
    for d in docs:
        title = d.get("title", "")
        materials = d.get("materials", {}) or {}
        summary = materials.get("summary") or ""
        concepts = " ".join(materials.get("key_concepts") or [])
        haystack = " · ".join([title, summary, concepts]).strip()

        emb = d.get("embedding") or []
        semantic = _cosine(query_embedding, emb) if (query_embedding and emb) else 0.0
        lexical = _lexical_score(haystack, q)
        score = 0.65 * semantic + 0.35 * lexical

        if score <= 0:
            continue
        snippet = (summary or concepts or title)[:180]
        results.append(SearchResult(
            lecture_id=d["id"],
            title=title,
            subject=d.get("subject"),
            semester=d.get("semester"),
            snippet=snippet,
            score=round(score, 4),
        ))
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
