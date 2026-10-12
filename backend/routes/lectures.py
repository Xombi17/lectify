"""Lecture routes — upload, list, detail, publish, quiz attempt, Phase 9 content."""
import logging
import os
from urllib.parse import quote
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

from core.deps import (
    get_current_user,
    get_user_accessible_class_ids,
    require_admin,
    require_teacher,
    require_teacher_or_admin,
    verify_lecture_access,
)
from core.queue_config import compute_priority_score
from models.chat import QuizAnswer, QuizAttemptRecord, QuizQuestionV2
from models.job import JobCreate, JobPublic
from models.lecture import (
    CheatsheetResponse,
    LectureDB,
    LectureSummary,
    PodcastScriptResponse,
    QuizAttempt,
    QuizResult,
    QuizV2Answer,
    QuizV2Attempt,
    QuizV2Result,
)
from models.user import UserPublic
from pydantic import BaseModel
from repositories.job_repository import JobRepository
from repositories.attempt_repository import AttemptRepository
from repositories.lecture_repository import LectureRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from services.ai_service import get_ai_service
from services.lecture_service import (
    ALLOWED_AUDIO_MIME,
    normalize_mime,
)
from services.queue_client import enqueue_job
from services.storage_service import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lectures", tags=["lectures"])

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
PRESIGN_EXPIRES_SECONDS = 900


class UploadUrlRequest(BaseModel):
    title: str
    class_id: str
    timetable_slot_id: str | None = None
    subject: str | None = None
    semester: str | None = None
    filename: str
    content_type: str
    size: int


@router.post("", response_model=LectureDB, status_code=status.HTTP_202_ACCEPTED)
async def upload_lecture(
    title: str = Form(...),
    class_id: str = Form(...),
    timetable_slot_id: str | None = Form(None),
    subject: str | None = Form(None),
    semester: str | None = Form(None),
    file: UploadFile = File(...),
    user: UserPublic = Depends(require_teacher_or_admin),
):
    if user.role != "admin":
        assignment_repo = TeacherAssignmentRepository()
        assignment = await assignment_repo.find_existing(class_id=class_id, teacher_id=user.id, active_only=True)
        if not assignment:
            raise HTTPException(status_code=403, detail="Not assigned to teach this class")

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
        class_id=class_id,
        timetable_slot_id=timetable_slot_id,
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
    class_ids = await get_user_accessible_class_ids(user)
    return await LectureRepository().list_published(class_ids=class_ids)


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


@router.post("/upload-url", status_code=status.HTTP_200_OK)
async def create_upload_url(
    payload: UploadUrlRequest,
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Mint a browser-direct S3 presigned POST for lecture audio.

    Creates the LectureDB row with status=uploading and returns
    {lecture_id, url, fields, key, expires_in} for a direct browser POST.
    Returns 501 on LocalStorage so the frontend falls back to multipart.
    """
    if user.role != "admin":
        assignment_repo = TeacherAssignmentRepository()
        assignment = await assignment_repo.find_existing(
            class_id=payload.class_id, teacher_id=user.id, active_only=True
        )
        if not assignment:
            raise HTTPException(status_code=403, detail="Not assigned to teach this class")

    if payload.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    mime = normalize_mime(payload.content_type or "", payload.filename or "")
    if not mime or mime not in ALLOWED_AUDIO_MIME:
        raise HTTPException(
            status_code=400, detail=f"Unsupported audio type: {payload.content_type}"
        )

    repo = LectureRepository()
    storage = get_storage()

    lecture_id = repo.new_id()
    safe_filename = (payload.filename or "lecture.mp3").replace("/", "_")
    key = f"classes/{payload.class_id}/lectures/{lecture_id}/recording/{safe_filename}"

    lecture = LectureDB(
        id=lecture_id,
        teacher_id=user.id,
        title=payload.title.strip(),
        subject=(payload.subject or "").strip() or None,
        semester=(payload.semester or "").strip() or None,
        class_id=payload.class_id,
        timetable_slot_id=payload.timetable_slot_id,
        audio_object_key=key,
        audio_filename=safe_filename,
        audio_mime=mime,
        status="uploading",
    )
    await repo.create(lecture)

    try:
        presigned = await storage.presign_post(
            key,
            content_type=mime,
            max_bytes=MAX_UPLOAD_BYTES,
            expires=PRESIGN_EXPIRES_SECONDS,
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=501, detail="Presigned upload not supported by storage backend"
        )

    return {
        "lecture_id": lecture_id,
        "url": presigned["url"],
        "fields": presigned["fields"],
        "key": key,
        "expires_in": PRESIGN_EXPIRES_SECONDS,
    }


@router.post("/{lecture_id}/upload-complete", response_model=LectureDB, status_code=status.HTTP_202_ACCEPTED)
async def complete_upload(
    lecture_id: str,
    user: UserPublic = Depends(require_teacher_or_admin),
):
    """Verify a browser-direct upload via head_object and enqueue transcribe once."""
    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if lecture.teacher_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    if lecture.status in ("queued", "processing", "ready"):
        return lecture

    if lecture.status == "dead_letter":
        raise HTTPException(
            status_code=409, detail="Lecture is in dead_letter; admin retry required"
        )
    if lecture.status not in ("uploading", "uploaded"):
        raise HTTPException(
            status_code=409, detail=f"Cannot complete from status {lecture.status}"
        )

    storage = get_storage()
    try:
        meta = await storage.head_object(lecture.audio_object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=409, detail="Object not uploaded")

    size = meta.get("size", 0)
    if size == 0 or size > MAX_UPLOAD_BYTES:
        try:
            await storage.delete(lecture.audio_object_key)
        except Exception:
            pass
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    actual_mime = normalize_mime(meta.get("content_type", ""), lecture.audio_filename)
    if actual_mime != lecture.audio_mime:
        raise HTTPException(status_code=400, detail="Content-Type mismatch")

    await repo.update_fields(lecture_id, {"status": "queued", "error_message": None})

    from services.metrics_service import record_lecture_uploaded
    record_lecture_uploaded(source="presigned_upload")

    score = compute_priority_score()
    await enqueue_job(
        JobCreate(
            lecture_id=lecture_id,
            version=1,
            priority_score=score,
            stage="transcribe",
        )
    )

    updated = await repo.get_by_id(lecture_id)
    return updated or lecture


@router.post("/{lecture_id}/retry", response_model=LectureDB)
async def retry_lecture(
    lecture_id: str,
    user: UserPublic = Depends(require_admin),
):
    """Reset a dead_letter lecture to queued and enqueue a fresh transcribe job (admin-only)."""
    from sqlalchemy import func, select

    from core.sql_db import session_maker
    from models.orm import JobORM

    repo = LectureRepository()
    lecture = await repo.get_by_id(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if lecture.status != "dead_letter":
        raise HTTPException(status_code=409, detail="Lecture is not in dead_letter")

    async with session_maker()() as session:
        result = await session.execute(
            select(func.max(JobORM.version)).where(
                JobORM.lecture_id == lecture_id, JobORM.stage == "transcribe"
            )
        )
        max_version = result.scalar()
    new_version = (max_version or 0) + 1

    await repo.update_fields(lecture_id, {"status": "queued", "error_message": None})

    score = compute_priority_score()
    await enqueue_job(
        JobCreate(
            lecture_id=lecture_id,
            version=new_version,
            priority_score=score,
            stage="transcribe",
        )
    )

    updated = await repo.get_by_id(lecture_id)
    return updated or lecture


@router.get("/{lecture_id}/audio-url")
async def get_audio_url(
    lecture_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Return a short-lived presigned GET for audio playback (class-gated)."""
    lecture = await verify_lecture_access(lecture_id, user)

    storage = get_storage()
    try:
        url = await storage.presign_get(
            lecture.audio_object_key, expires=PRESIGN_EXPIRES_SECONDS
        )
    except NotImplementedError:
        raise HTTPException(
            status_code=501, detail="Presigned playback not supported by storage backend"
        )
    return {"url": url, "expires_in": PRESIGN_EXPIRES_SECONDS}


@router.get("/{lecture_id}", response_model=LectureDB)
async def get_lecture(lecture_id: str, user: UserPublic = Depends(get_current_user)):
    lecture = await verify_lecture_access(lecture_id, user)
    if lecture.status == "ready":
        try:
            secs = await JobRepository().span_seconds(lecture_id)
        except Exception:  # informational field; never break the detail page
            secs = None
        if secs is None:  # legacy lectures without jobs
            secs = max((lecture.updated_at - lecture.created_at).total_seconds(), 0.0)
        lecture = lecture.model_copy(update={"processing_seconds": round(secs, 1)})
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
    lecture = await verify_lecture_access(lecture_id, user)
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
    lecture = await verify_lecture_access(lecture_id, user)

    storage = get_storage()
    try:
        body_iter, size, _ = await storage.stream(lecture.audio_object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio file missing")

    headers = {
        # RFC 5987: header values must be latin-1, so ascii fallback + utf-8 filename*
        "Content-Disposition": (
            "inline; filename=\""
            + lecture.audio_filename.encode("ascii", "replace").decode().replace('"', "_")
            + "\"; filename*=UTF-8''" + quote(lecture.audio_filename)
        ),
    }
    if size is not None:
        headers["Content-Length"] = str(size)
    return StreamingResponse(body_iter, media_type=lecture.audio_mime, headers=headers)


# ── Helper functions for job status mapping ────────────────────────────


def _status_from_lecture_status(lecture_status: str) -> str:
    """Map LectureDB status to JobPublic status."""
    mapping = {
        "uploading": "queued",
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
    if lecture.status in ("queued", "uploading", "uploaded"):
        return "transcribe"
    if lecture.transcript and not (lecture.materials and lecture.materials.summary):
        return "generate_materials"
    if not lecture.embedding:
        return "embed"
    return "neo4j_sync"
