"""Chat (RAG over lecture transcript) + translation endpoints."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from core.deps import get_current_user, verify_lecture_access
from models.chat import (
    ChatAskRequest,
    ChatAskResponse,
    ChatMessageDB,
    TranslateRequest,
)
from models.user import UserPublic
from repositories.chat_repository import ChatRepository
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service

router = APIRouter(tags=["chat"])


@router.post("/lectures/{lecture_id}/chat", response_model=ChatAskResponse)
async def ask_doubt(
    lecture_id: str,
    payload: ChatAskRequest,
    user: UserPublic = Depends(get_current_user),
):
    lecture = await verify_lecture_access(lecture_id, user)
    if not lecture.transcript:
        raise HTTPException(status_code=400, detail="Lecture transcript not ready yet")

    chat_repo = ChatRepository()
    history = await chat_repo.list_for(lecture_id, user.id, limit=20)
    ai = get_ai_service()
    answer = await ai.chat(
        transcript=lecture.transcript,
        history=[{"role": m.role, "content": m.content} for m in history],
        question=payload.question,
    )

    now = datetime.now(timezone.utc)
    user_msg = ChatMessageDB(
        id=chat_repo.new_id(),
        lecture_id=lecture_id,
        user_id=user.id,
        role="user",
        content=payload.question.strip(),
        created_at=now,
    )
    assistant_msg = ChatMessageDB(
        id=chat_repo.new_id(),
        lecture_id=lecture_id,
        user_id=user.id,
        role="assistant",
        content=answer or "I couldn't generate a response.",
        created_at=datetime.now(timezone.utc),
    )
    await chat_repo.add(user_msg)
    await chat_repo.add(assistant_msg)
    return ChatAskResponse(user_message=user_msg, assistant_message=assistant_msg)


@router.get("/lectures/{lecture_id}/chat", response_model=List[ChatMessageDB])
async def chat_history(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    await verify_lecture_access(lecture_id, user)
    return await ChatRepository().list_for(lecture_id, user.id, limit=100)


@router.post("/lectures/{lecture_id}/translate")
async def translate_lecture(
    lecture_id: str,
    payload: TranslateRequest,
    user: UserPublic = Depends(get_current_user),
):
    """Translate summary + smart_notes + key_concepts + flashcards into `target_language`.

    Result is cached on the lecture doc under `translations[lang_lower]` so subsequent
    requests are instant and don't burn tokens.
    """
    lecture = await verify_lecture_access(lecture_id, user)
    lec_repo = LectureRepository()
    if lecture.status != "ready":
        raise HTTPException(status_code=400, detail="Lecture is not ready")

    lang_key = payload.target_language.strip().lower()
    if lang_key in (lecture.translations or {}):
        return lecture.translations[lang_key]

    pack = {
        "summary": lecture.materials.summary or "",
        "smart_notes": lecture.materials.smart_notes,
        "key_concepts": lecture.materials.key_concepts,
        "flashcards": [c.model_dump() for c in lecture.materials.flashcards],
    }
    ai = get_ai_service()
    translated = await ai.translate_pack(pack, payload.target_language.strip())
    # Persist cache
    translations = dict(lecture.translations or {})
    translations[lang_key] = translated
    await lec_repo.update_fields(lecture_id, {"translations": translations})
    return translated
