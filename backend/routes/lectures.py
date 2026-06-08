"""Lecture routes — upload, list, detail, publish, quiz attempt."""
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from core.deps import get_current_user, require_teacher
from core.queue_config import compute_priority_score
from models.job import JobCreate, JobPublic
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
)
from services.queue_client import enqueue_job
from services.storage_service import get_storage

router = APIRouter(prefix="/lectures", tags=["lectures"])


@router.post("", response_model=LectureDB, status_code=status.HTTP_202_ACCEPTED)
async def upload_lecture(
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
        status="queued",
    )
    await repo.create(lecture)

    # Record upload metric
    from services.metrics_service import record_lecture_uploaded
    record_lecture_uploaded(source="file_upload")

    # Enqueue processing job
    score = compute_priority_score()
    job_payload = JobCreate(
        lecture_id=lecture_id,
        version=1,
        priority_score=score,
        stage="transcribe",
    )
    job = await enqueue_job(job_payload)

    logger = __import__("logging").getLogger(__name__)
    logger.info("Lecture %s uploaded, enqueued job %s", lecture_id, job.id)

    # Return lecture with queued status
    return lecture


@router.get("/mine", response_model=list[LectureSummary])
async def my_lectures(user: UserPublic = Depends(require_teacher)):
    return await LectureRepository().list_by_teacher(user.id)


@router.get("/published", response_model=list[LectureSummary])
async def published_lectures(user: UserPublic = Depends(get_current_user)):
    return await LectureRepository().list_published()


@router.get("/{lecture_id}/job-status", response_model=JobPublic)
async def get_lecture_job_status(
    lecture_id: str,
    user: UserPublic = Depends(require_teacher),
):
    """Get the current queue status for a lecture's processing job.

    Teachers can poll this endpoint to track processing progress.
    Returns the job's current stage, status, and attempt count.
    """
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")

    # Return a JobPublic from the lecture's current state
    return JobPublic(
        id=f"lecture:{lecture_id}",
        lecture_id=lecture_id,
        stage=_stage_from_status(lecture),
        status=_status_from_lecture_status(lecture.status),
        attempt=0,
        error_message=lecture.error_message,
        created_at=lecture.created_at,
        updated_at=lecture.updated_at,
    )


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
    from core.deps import AUDIT_PUBLISH, log_audit

    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if lecture.status != "ready":
        raise HTTPException(status_code=400, detail="Lecture is not ready to publish")
    await repo.update_fields(lecture_id, {"published": True})

    await log_audit(
        action=AUDIT_PUBLISH,
        entity_type="lecture",
        entity_id=lecture_id,
        details=f"Published lecture: {lecture.title}",
        admin_id=user.id,
    )

    return await repo.get_by_id(lecture_id)


@router.post("/{lecture_id}/unpublish", response_model=LectureDB)
async def unpublish_lecture(lecture_id: str, user: UserPublic = Depends(require_teacher)):
    from core.deps import AUDIT_UNPUBLISH, log_audit

    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    await repo.update_fields(lecture_id, {"published": False})

    await log_audit(
        action=AUDIT_UNPUBLISH,
        entity_type="lecture",
        entity_id=lecture_id,
        details=f"Unpublished lecture: {lecture.title}",
        admin_id=user.id,
    )

    return await repo.get_by_id(lecture_id)


@router.delete("/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture(lecture_id: str, user: UserPublic = Depends(require_teacher)):
    from core.deps import AUDIT_DELETE, log_audit

    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture or lecture.teacher_id != user.id:
        raise HTTPException(status_code=404, detail="Lecture not found")

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="lecture",
        entity_id=lecture_id,
        details=f"Deleted lecture: {lecture.title}",
        admin_id=user.id,
    )

    await repo.delete(lecture_id)
    # also remove the stored file (best-effort)
    storage = get_storage()
    try:
        await storage.delete(lecture.audio_object_key)
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
    # RBAC: students may only attempt published lectures; teachers may attempt their own
    if user.role == "student" and not lecture.published:
        raise HTTPException(status_code=403, detail="Lecture not available")
    if user.role == "teacher" and lecture.teacher_id != user.id and not lecture.published:
        raise HTTPException(status_code=403, detail="Forbidden")
    quiz = lecture.materials.quiz
    if not quiz:
        raise HTTPException(status_code=400, detail="No quiz available")
    correct_answers = [q.answer_index for q in quiz]
    if len(attempt.answers) != len(correct_answers):
        raise HTTPException(status_code=400, detail="Answer count mismatch")
    score = sum(1 for u, c in zip(attempt.answers, correct_answers) if u == c)
    total = len(correct_answers)
    percentage = round((score / total) * 100, 1) if total else 0.0

    # Persist for analytics
    from repositories.attempt_repository import AttemptRepository
    from models.chat import QuizAttemptRecord
    attempt_repo = AttemptRepository()
    rec = QuizAttemptRecord(
        id=attempt_repo.new_id(),
        lecture_id=lecture_id,
        user_id=user.id,
        score=score,
        total=total,
        percentage=percentage,
    )
    await attempt_repo.add(rec)

    return QuizResult(
        score=score,
        total=total,
        percentage=percentage,
        correct_answers=correct_answers,
        user_answers=attempt.answers,
    )


# --- Audio streaming (works for any storage backend) ---
@router.get("/{lecture_id}/audio")
async def stream_audio(lecture_id: str, user: UserPublic = Depends(get_current_user)):
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if user.role == "student" and not lecture.published:
        raise HTTPException(status_code=403, detail="Forbidden")

    storage = get_storage()
    try:
        body_iter, size, _ = await storage.stream(lecture.audio_object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio file missing")

    headers = {
        "Content-Disposition": f'inline; filename="{lecture.audio_filename}"',
    }
    if size is not None:
        headers["Content-Length"] = str(size)
    return StreamingResponse(body_iter, media_type=lecture.audio_mime, headers=headers)


# ── Helper functions for job status mapping ────────────────────────────


def _status_from_lecture_status(lecture_status: str) -> str:
    """Map LectureDB status to JobPublic status."""
    mapping = {
        "queued": "queued",
        "uploaded": "queued",
        "processing": "processing",
        "retrying": "retrying",
        "ready": "completed",
        "error": "failed",
        "dead_letter": "dead_letter",
    }
    return mapping.get(lecture_status, "queued")


def _stage_from_status(lecture) -> str:
    """Determine current processing stage from lecture state."""
    if lecture.status == "queued":
        return "transcribe"
    if lecture.transcript and not (lecture.materials and lecture.materials.summary):
        return "generate_materials"
    if not lecture.embedding:
        return "embed"
    return "neo4j_sync"
