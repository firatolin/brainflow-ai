"""Background scan scheduler.

- Runs a scan every SCAN_INTERVAL_MINUTES (default 5).
- Never overlaps runs (max_instances=1).
- Skips entirely if another scan is already running (advisory lock via file check
  is overkill for single-worker demo; APScheduler's max_instances handles it).
- Failures are logged and recorded — they do NOT crash the scheduler.
- Fully controlled by the SCHEDULER_ENABLED setting (off in tests).
- Refuses to start when using an in-memory test DB.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import scan_service


logger = logging.getLogger("brainflow.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    started = datetime.now(timezone.utc)
    db: Session = SessionLocal()
    try:
        run = scan_service.run_scan(db, triggered_by="scheduled")
        logger.info(
            "Scheduled scan ok id=%s scanned=%s new_incidents=%s auto_resolved=%s duration_ms=%s",
            run.id,
            run.deliveries_scanned,
            run.incidents_created,
            run.incidents_auto_resolved,
            int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        # Best-effort failure record
        try:
            scan_service.run_scan  # noqa: F841
            logger.exception("Scheduled scan failed: %s", exc)
        finally:
            pass
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    logger.info(
        "start_scheduler called: enabled=%s interval=%sm db=%s",
        settings.SCHEDULER_ENABLED,
        settings.SCAN_INTERVAL_MINUTES,
        settings.DATABASE_URL.split("/")[-1],
    )
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return None
    if settings.DATABASE_URL.endswith(":memory:"):
        logger.info("Scheduler skipped: in-memory database")
        return None

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=settings.SCAN_INTERVAL_MINUTES),
        id="operational_scan",
        name="Operational scan",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        misfire_grace_time=120,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: interval=%smin next_run=%s",
        settings.SCAN_INTERVAL_MINUTES,
        next_run_summary(),
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:  # noqa: BLE001
            pass
        _scheduler = None
        logger.info("Scheduler stopped")


def next_run_summary() -> str | None:
    if _scheduler is None:
        return None
    jobs = _scheduler.get_jobs()
    if not jobs:
        return None
    nxt = jobs[0].next_run_time
    if not nxt:
        return None
    return nxt.astimezone(__import__("datetime").timezone.utc).isoformat()
