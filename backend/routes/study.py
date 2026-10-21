"""Study routes: notes editing, bookmarks, flashcard spaced-repetition, PDF export."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from io import BytesIO

from core.deps import (
    get_current_user,
    lecture_in_scope,
    require_teacher,
    student_class_scope,
    verify_lecture_access,
)
from models.bookmark import (
    BookmarkCreate,
    BookmarkDB,
    BookmarkWithLecture,
    DueCard,
    FlashcardReviewDB,
    MaterialsUpdate,
    ReviewSubmit,
)
from models.lecture import LectureDB
from models.user import UserPublic
from repositories.bookmark_repository import BookmarkRepository
from repositories.flashcard_review_repository import FlashcardReviewRepository
from repositories.lecture_repository import LectureRepository
from services.pdf_export import render_lecture_pdf
from services.spaced_repetition import schedule_next


router = APIRouter(tags=["study"])


# ---------------------------------------------------------------- Notes edit
@router.patch("/lectures/{lecture_id}/materials", response_model=LectureDB)
async def edit_materials(
    lecture_id: str,
    payload: MaterialsUpdate,
    user: UserPublic = Depends(require_teacher),
):
    """Teacher can edit AI-generated summary, smart notes, and key concepts.

    Quiz and flashcards are NOT editable here — they're used for grading and
    spaced-repetition, so changing them mid-flight would break student state.
    """
    lecture = await verify_lecture_access(lecture_id, user)
    if lecture.status != "ready":
        raise HTTPException(status_code=400, detail="Lecture is not ready")

    repo = LectureRepository()
    updated = lecture.materials.model_copy()
    if payload.summary is not None:
        updated.summary = payload.summary.strip() or None
    if payload.smart_notes is not None:
        updated.smart_notes = [n.strip() for n in payload.smart_notes if n.strip()]
    if payload.key_concepts is not None:
        updated.key_concepts = [c.strip() for c in payload.key_concepts if c.strip()]

    await repo.update_fields(lecture_id, {"materials": updated})
    # Invalidate cached translations — they're stale after an edit
    if lecture.translations:
        await repo.update_fields(lecture_id, {"translations": {}})
    return await repo.get_by_id(lecture_id)


# ---------------------------------------------------------------- PDF export
@router.get("/lectures/{lecture_id}/pdf")
async def export_pdf(lecture_id: str, user: UserPublic = Depends(get_current_user)):
    lecture = await verify_lecture_access(lecture_id, user)
    if lecture.status != "ready":
        raise HTTPException(status_code=400, detail="Lecture is not ready")

    pdf_bytes = render_lecture_pdf(lecture)
    # ASCII-only filename for Content-Disposition (latin-1 HTTP header constraint).
    safe_title = "".join(c if ord(c) < 128 else "-" for c in lecture.title[:60]).replace('"', "'")
    filename = f"{safe_title} - Notes.pdf"

    def _iter():
        yield pdf_bytes

    return StreamingResponse(
        _iter(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# ---------------------------------------------------------------- Bookmarks
@router.post("/bookmarks", response_model=BookmarkDB, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    payload: BookmarkCreate,
    user: UserPublic = Depends(get_current_user),
):
    await verify_lecture_access(payload.lecture_id, user)

    bm_repo = BookmarkRepository()
    existing = await bm_repo.find_existing(
        user.id, payload.lecture_id, payload.kind, payload.ref_index
    )
    if existing:
        return existing

    bm = BookmarkDB(
        id=bm_repo.new_id(),
        user_id=user.id,
        lecture_id=payload.lecture_id,
        kind=payload.kind,
        text=payload.text.strip(),
        ref_index=payload.ref_index,
    )
    return await bm_repo.add(bm)


@router.get("/bookmarks/me", response_model=List[BookmarkWithLecture])
async def list_my_bookmarks(user: UserPublic = Depends(get_current_user)):
    bm_repo = BookmarkRepository()
    lec_repo = LectureRepository()
    bookmarks = await bm_repo.list_for_user(user.id)
    scope = await student_class_scope(user)
    out: list[BookmarkWithLecture] = []
    cache: dict[str, tuple[str, str | None] | None] = {}
    for bm in bookmarks:
        if bm.lecture_id not in cache:
            lec = await lec_repo.get_by_id(bm.lecture_id)
            if lec and not lecture_in_scope(lec, scope):
                cache[bm.lecture_id] = None
            else:
                cache[bm.lecture_id] = (
                    (lec.title if lec else "(deleted lecture)"),
                    (lec.subject if lec else None),
                )
        if cache[bm.lecture_id] is None:
            continue
        title, subject = cache[bm.lecture_id]
        out.append(BookmarkWithLecture(**bm.model_dump(), lecture_title=title, lecture_subject=subject))
    return out


@router.get("/lectures/{lecture_id}/bookmarks", response_model=List[BookmarkDB])
async def list_lecture_bookmarks(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    await verify_lecture_access(lecture_id, user)
    return await BookmarkRepository().list_for_user_lecture(user.id, lecture_id)


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: str, user: UserPublic = Depends(get_current_user)):
    ok = await BookmarkRepository().delete(bookmark_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bookmark not found")


# ----------------------------------------------------------- Flashcard reviews
@router.post("/flashcards/review", response_model=FlashcardReviewDB)
async def submit_review(payload: ReviewSubmit, user: UserPublic = Depends(get_current_user)):
    lecture = await verify_lecture_access(payload.lecture_id, user)
    if payload.card_index < 0 or payload.card_index >= len(lecture.materials.flashcards):
        raise HTTPException(status_code=400, detail="Invalid card_index")

    rev_repo = FlashcardReviewRepository()
    prev = await rev_repo.get(user.id, payload.lecture_id, payload.card_index)
    if prev is None:
        prev = FlashcardReviewDB(
            id=rev_repo.new_id(),
            user_id=user.id,
            lecture_id=payload.lecture_id,
            card_index=payload.card_index,
            due_at=datetime.now(timezone.utc),
        )

    updated = schedule_next(prev, payload.quality)
    await rev_repo.upsert(updated)
    return updated


@router.get("/flashcards/due", response_model=List[DueCard])
async def list_due_flashcards(
    limit: int = 50,
    user: UserPublic = Depends(get_current_user),
):
    """Hydrate due flashcards across ALL lectures into a unified review queue."""
    rev_repo = FlashcardReviewRepository()
    lec_repo = LectureRepository()
    due = await rev_repo.list_due_for_user(user.id, limit=limit)
    scope = await student_class_scope(user)
    out: list[DueCard] = []
    lec_cache: dict[str, "LectureDB | None"] = {}
    for r in due:
        if r.lecture_id not in lec_cache:
            lec_cache[r.lecture_id] = await lec_repo.get_by_id(r.lecture_id)
        lecture = lec_cache[r.lecture_id]
        if not lecture or r.card_index >= len(lecture.materials.flashcards):
            continue
        if user.role == "student" and not lecture.published:
            continue
        if not lecture_in_scope(lecture, scope):
            continue
        card = lecture.materials.flashcards[r.card_index]
        out.append(DueCard(
            lecture_id=r.lecture_id,
            lecture_title=lecture.title,
            card_index=r.card_index,
            front=card.front,
            back=card.back,
            due_at=r.due_at,
            repetitions=r.repetitions,
            ease_factor=r.ease_factor,
        ))
    return out


@router.get("/lectures/{lecture_id}/flashcards/state", response_model=List[FlashcardReviewDB])
async def lecture_flashcard_state(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """All reviewed cards for a lecture (for showing due-status in the deck)."""
    await verify_lecture_access(lecture_id, user)
    all_revs = await FlashcardReviewRepository().list_all_for_user(user.id)
    return [r for r in all_revs if r.lecture_id == lecture_id]
