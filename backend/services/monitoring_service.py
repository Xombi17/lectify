"""
SLA tracking, daily summary generation, and Slack notifications.

Tracks the "95% same-day processing" SLA:
  - Lecture uploaded today -> fully processed (status='ready') before midnight
  - SLA % = lectures completed same-day / lectures uploaded that day * 100
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from prometheus_client import Gauge

from core.config import get_settings

logger = logging.getLogger(__name__)

# -- SLA Metric ----------------------------------------------------------------
sla_same_day_percent = Gauge(
    "lectify_sla_same_day_percent",
    "Percentage of lectures processed same-day",
    ["date_label"],  # "YYYY-MM-DD" - max 7 rolling days per scrape
)


async def compute_daily_sla(target_date: date) -> dict:
    """
    Compute SLA for a specific date.

    SLA = lectures with status="ready" and created on target_date
          / all lectures created on target_date * 100

    A lecture counts as "completed same-day" when its status reaches "ready"
    before the end of the target_date.

    Returns:
        {
            "date": "2026-06-08",
            "total_uploaded": 42,
            "completed_same_day": 40,
            "sla_percent": 95.2,
            "still_processing": 2,
            "failed": 0,
        }
    """
    from repositories.lecture_repository import LectureRepository

    repo = LectureRepository()

    # Get lectures uploaded on target_date
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    lectures = await repo.get_lectures_by_date_range(day_start, day_end)
    total = len(lectures)

    if total == 0:
        result = {
            "date": target_date.isoformat(),
            "total_uploaded": 0,
            "completed_same_day": 0,
            "sla_percent": 100.0,
            "still_processing": 0,
            "failed": 0,
        }
        sla_same_day_percent.labels(date_label=target_date.isoformat()).set(100.0)
        return result

    completed = 0
    still_processing = 0
    failed = 0

    for lecture in lectures:
        if lecture.status == "ready":
            completed += 1
        elif lecture.status in ("dead_letter", "error"):
            failed += 1
        else:
            still_processing += 1

    sla_pct = round((completed / total) * 100, 1) if total > 0 else 100.0

    result = {
        "date": target_date.isoformat(),
        "total_uploaded": total,
        "completed_same_day": completed,
        "sla_percent": sla_pct,
        "still_processing": still_processing,
        "failed": failed,
    }

    sla_same_day_percent.labels(date_label=target_date.isoformat()).set(sla_pct)
    return result


async def compute_rolling_sla(days: int = 7) -> list[dict]:
    """Compute SLA for the last N days."""
    results = []
    for i in range(days):
        d = date.today() - timedelta(days=i)
        result = await compute_daily_sla(d)
        results.append(result)
    return results


async def generate_daily_summary(target_date: date | None = None) -> dict:
    """Generate a full daily processing summary with SLA + queue stats."""
    if target_date is None:
        target_date = date.today()

    sla = await compute_daily_sla(target_date)

    # Gather queue stats from the queue client
    from services.queue_client import get_queue_depth

    queue_depth_val = await get_queue_depth()

    summary = {
        "date": target_date.isoformat(),
        "sla": sla,
        "queue": {
            "current_depth": queue_depth_val,
        },
        "system": {
            "active_lectures": sla["total_uploaded"],
        },
    }
    return summary


def format_slack_message(summary: dict) -> dict:
    """Format daily summary as a Slack block kit message."""
    sla = summary["sla"]
    queue = summary["queue"]

    color = (
        "good"
        if sla["sla_percent"] >= 95
        else "warning"
        if sla["sla_percent"] >= 80
        else "danger"
    )

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"\U0001f4ca Lectify Daily Summary — {summary['date']}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*SLA (same-day):* {sla['sla_percent']}%"},
                {"type": "mrkdwn", "text": f"*Total uploaded:* {sla['total_uploaded']}"},
                {"type": "mrkdwn", "text": f"*Completed:* {sla['completed_same_day']}"},
                {"type": "mrkdwn", "text": f"*Still processing:* {sla['still_processing']}"},
                {"type": "mrkdwn", "text": f"*Failed:* {sla['failed']}"},
                {"type": "mrkdwn", "text": f"*Queue depth:* {queue['current_depth']}"},
            ],
        },
        {"type": "divider"},
    ]

    return {
        "blocks": blocks,
        "attachments": [
            {
                "color": color,
                "text": f"SLA: {sla['sla_percent']}% — target is {get_settings().SLA_TARGET_PERCENT}%",
            }
        ],
    }


async def send_slack_webhook(summary: dict) -> bool:
    """Send daily summary to Slack via webhook."""
    settings = get_settings()
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured - skipping Slack notification")
        return False

    message = format_slack_message(summary)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json=message, timeout=10)
            resp.raise_for_status()
            logger.info("Daily summary sent to Slack for %s", summary["date"])
            return True
    except Exception as e:
        logger.error("Failed to send Slack webhook: %s", e)
        return False
