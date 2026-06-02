"""Lecture routes — upload, list, detail, publish, quiz attempt."""
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from core.deps import get_current_user, require_teacher
from models.lecture import (
    LectureDB,
    LectureSummary,
    QuizAttempt,
    QuizResult,
)
from models.user import UserPublic
from repositories.lecture_repository import LectureRepository
from services.lecture_service import (
    ALLOWED_AUDIO_MIME,
    normalize_mime,
    process_lecture_background,
)
from services.storage_service import get_storage

router = APIRouter(prefix="/lectures", tags=["lectures"])


@router.post("", response_model=LectureDB, status_code=status.HTTP_202_ACCEPTED)
async def upload_lecture(
    background: BackgroundTasks,
    title: str = Form(...),
    subject: str | None = Form(None),
    semester: str | None = Form(None),
    file: UploadFile = File(...),
    user: UserPublic = Depends(require_teacher),
):
    if file.size and file.size > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    mime = normalize_mime(file.content_type or "", file.filename or "")
    if not mime or mime not in ALLOWED_AUDIO_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {file.content_type}")

    repo = LectureRepository()
    storage = get_storage()

    lecture_id = repo.new_id()
    safe_filename = (file.filename or "lecture.mp3").replace("/", "_")
    key = f"lectures/{lecture_id}/{safe_filename}"

    await storage.save(key, file.file, mime)

    lecture = LectureDB(
        id=lecture_id,
        teacher_id=user.id,
        title=title.strip(),
        subject=(subject or "").strip() or None,
        semester=(semester or "").strip() or None,
        audio_object_key=key,
        audio_filename=safe_filename,
        audio_mime=mime,
        status="uploaded",
    )
    await repo.create(lecture)

    background.add_task(process_lecture_background, lecture_id)
    return lecture


@router.get("/mine", response_model=list[LectureSummary])
async def my_lectures(user: UserPublic = Depends(require_teacher)):
    return await LectureRepository().list_by_teacher(user.id)


@router.get("/published", response_model=list[LectureSummary])
async def published_lectures(user: UserPublic = Depends(get_current_user)):
    return await LectureRepository().list_published()


@router.get("/{lecture_id}", response_model=LectureDB)
async def get_lecture(lecture_id: str, user: UserPublic = Depends(get_current_user)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    # students can only view published; teachers can view their own
    if user.role == "student" and not lecture.published:
        raise HTTPException(status_code=403, detail="Lecture not available")
    if user.role == "teacher" and lecture.teacher_id != user.id and not lecture.published:
        raise HTTPException(status_code=403, detail="Forbidden")
    return lecture


@router.post("/{lecture_id}/publish", response_model=LectureDB)
async def publish_lecture(lecture_id: str, user: UserPublic = Depends(require_teacher)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if lecture.status != "ready":
        raise HTTPException(status_code=400, detail="Lecture is not ready to publish")
    await repo.update_fields(lecture_id, {"published": True})
    return await repo.get_by_id(lecture_id)


@router.post("/{lecture_id}/unpublish", response_model=LectureDB)
async def unpublish_lecture(lecture_id: str, user: UserPublic = Depends(require_teacher)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    await repo.update_fields(lecture_id, {"published": False})
    return await repo.get_by_id(lecture_id)


@router.delete("/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture(lecture_id: str, user: UserPublic = Depends(require_teacher)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    await repo.delete(lecture_id)
    # also remove the stored file (best-effort, local backend only)
    storage = get_storage()
    try:
        p = storage.local_path(lecture.audio_object_key)
        if p.exists():
            p.unlink()
    except Exception:
        pass


@router.post("/{lecture_id}/quiz/attempt", response_model=QuizResult)
async def submit_quiz(
    lecture_id: str,
    attempt: QuizAttempt,
    user: UserPublic = Depends(get_current_user),
):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    quiz = lecture.materials.quiz
    if not quiz:
        raise HTTPException(status_code=400, detail="No quiz available")
    correct_answers = [q.answer_index for q in quiz]
    if len(attempt.answers) != len(correct_answers):
        raise HTTPException(status_code=400, detail="Answer count mismatch")
    score = sum(1 for u, c in zip(attempt.answers, correct_answers) if u == c)
    total = len(correct_answers)
    return QuizResult(
        score=score,
        total=total,
        percentage=round((score / total) * 100, 1) if total else 0.0,
        correct_answers=correct_answers,
        user_answers=attempt.answers,
    )


# --- Audio streaming (local storage backend only) ---
@router.get("/{lecture_id}/audio")
async def stream_audio(lecture_id: str, user: UserPublic = Depends(get_current_user)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if user.role == "student" and not lecture.published:
        raise HTTPException(status_code=403, detail="Forbidden")

    storage = get_storage()
    path = storage.local_path(lecture.audio_object_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(str(path), media_type=lecture.audio_mime, filename=lecture.audio_filename)
