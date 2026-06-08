"""
Alert evaluation service.

Periodically checks thresholds and fires alerts via Slack webhook.
Uses asyncio background task (no APScheduler dependency).
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    alert_name: str
    severity: str  # "info" | "warning" | "critical"
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)


class AlertManager:
    """
    Evaluate alert conditions with deduplication.

    Alerts are suppressed within a cooldown window to prevent alert storms.
    """

    def __init__(self, cooldown_seconds: int = 300):
        self._cooldown_seconds = cooldown_seconds
        self._last_fired: dict[str, float] = {}

    def _should_fire(self, alert_name: str) -> bool:
        now = time.time()
        last = self._last_fired.get(alert_name, 0)
        return (now - last) > self._cooldown_seconds

    def _mark_fired(self, alert_name: str) -> None:
        self._last_fired[alert_name] = time.time()

    async def _send_alert(self, event: AlertEvent) -> bool:
        """Send alert via Slack webhook."""
        settings = get_settings()
        if not settings.SLACK_WEBHOOK_URL:
            return False

        color_map = {"info": "#36a64f", "warning": "#f2c744", "critical": "#d93a3a"}
        message = {
            "attachments": [
                {
                    "color": color_map.get(event.severity, "#cccccc"),
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"\U0001f6a8 {event.alert_name}",
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:* {event.severity}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Value:* {event.value:.1f}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Threshold:* {event.threshold}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Time:* {datetime.fromtimestamp(event.timestamp).isoformat()}",
                                },
                            ],
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": event.message},
                        },
                    ],
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    settings.SLACK_WEBHOOK_URL, json=message, timeout=10
                )
                resp.raise_for_status()
                logger.info(
                    "Alert sent: %s (severity=%s)",
                    event.alert_name,
                    event.severity,
                )
                return True
        except Exception:
            logger.exception("Failed to send alert: %s", event.alert_name)
            return False

    # ---- Alert Evaluators --------------------------------------------------

    async def check_queue_depth(
        self, current_depth: int, threshold: int, queue_type: str
    ) -> AlertEvent | None:
        """Fire if queue depth exceeds threshold."""
        if current_depth <= threshold:
            return None
        alert_name = f"queue_depth_{queue_type}"
        if not self._should_fire(alert_name):
            return None
        event = AlertEvent(
            alert_name=alert_name,
            severity="warning" if current_depth < threshold * 2 else "critical",
            message=(
                f"{queue_type} queue depth is {current_depth} (threshold: {threshold}). "
                "May need to scale workers."
            ),
            value=float(current_depth),
            threshold=float(threshold),
        )
        self._mark_fired(alert_name)
        await self._send_alert(event)
        return event

    async def check_dlq_growth(
        self, dlq_size: int, growth_threshold: int, queue_type: str
    ) -> AlertEvent | None:
        """Fire if DLQ grows beyond threshold."""
        if dlq_size <= growth_threshold:
            return None
        alert_name = f"dlq_growth_{queue_type}"
        if not self._should_fire(alert_name):
            return None
        event = AlertEvent(
            alert_name=alert_name,
            severity="critical",
            message=(
                f"{queue_type} dead-letter queue has {dlq_size} items "
                f"(threshold: {growth_threshold}). Requires manual investigation."
            ),
            value=float(dlq_size),
            threshold=float(growth_threshold),
        )
        self._mark_fired(alert_name)
        await self._send_alert(event)
        return event

    async def check_sla_breach(
        self, sla_percent: float, target_percent: float, date_label: str
    ) -> AlertEvent | None:
        """Fire if SLA drops below target."""
        if sla_percent >= target_percent:
            return None
        alert_name = f"sla_breach_{date_label}"
        if not self._should_fire(alert_name):
            return None
        event = AlertEvent(
            alert_name=alert_name,
            severity="warning",
            message=(
                f"SLA on {date_label} is {sla_percent}% — "
                f"below target of {target_percent}%."
            ),
            value=sla_percent,
            threshold=target_percent,
        )
        self._mark_fired(alert_name)
        await self._send_alert(event)
        return event


# Singleton instance
alert_manager = AlertManager()
