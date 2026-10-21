"""Student analytics endpoint."""
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from core.deps import get_current_user, lecture_in_scope, student_class_scope
from models.chat import StudentAnalytics, WeakLecture
from models.user import UserPublic
from repositories.attempt_repository import AttemptRepository
from repositories.lecture_repository import LectureRepository

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/me", response_model=StudentAnalytics)
async def my_analytics(user: UserPublic = Depends(get_current_user)):
    attempts = await AttemptRepository().list_for_user(user.id)
    if not attempts:
        return StudentAnalytics(
            attempts_count=0,
            lectures_attempted=0,
            avg_percentage=0.0,
            last_attempt_at=None,
            streak_days=0,
            weak_lectures=[],
            strong_lectures=[],
        )

    by_lecture: dict[str, list[float]] = defaultdict(list)
    for a in attempts:
        by_lecture[a.lecture_id].append(a.percentage)

    lec_repo = LectureRepository()
    scope = await student_class_scope(user)
    rows: list[WeakLecture] = []
    for lid, scores in by_lecture.items():
        lec = await lec_repo.get_by_id(lid)
        if not lec or not lecture_in_scope(lec, scope):
            continue
        rows.append(WeakLecture(
            lecture_id=lid,
            title=lec.title,
            avg_percentage=round(sum(scores) / len(scores), 1),
            attempts=len(scores),
        ))

    weak = sorted(rows, key=lambda r: r.avg_percentage)[:3]
    strong = sorted(rows, key=lambda r: r.avg_percentage, reverse=True)[:3]
    avg = round(sum(a.percentage for a in attempts) / len(attempts), 1)

    # Streak: consecutive days ending today/yesterday with at least one attempt
    from datetime import timedelta
    days = sorted({a.created_at.date() for a in attempts}, reverse=True)
    today = datetime.now(timezone.utc).date()
    # start cursor at today if today has activity, else yesterday
    start = today if today in days else (today - timedelta(days=1)) if (today - timedelta(days=1)) in days else None
    streak = 0
    if start is not None:
        cursor = start
        for d in days:
            if d == cursor:
                streak += 1
                cursor = cursor - timedelta(days=1)
            elif d < cursor:
                break

    return StudentAnalytics(
        attempts_count=len(attempts),
        lectures_attempted=len(by_lecture),
        avg_percentage=avg,
        last_attempt_at=attempts[0].created_at,
        streak_days=streak,
        weak_lectures=weak,
        strong_lectures=strong,
    )
