from datetime import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.task import ScheduledTask
from app.services.task_runner import run_scheduled_task
from app.services.settings import cleanup_history


scheduler = BackgroundScheduler(
    timezone="UTC",
)


def validate_timezone(
    timezone_name: str,
) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)

    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unknown timezone: {timezone_name}"
        ) from exc


def build_trigger(
    task: ScheduledTask,
):
    tz = validate_timezone(
        task.timezone
    )

    if task.schedule_type == "once":
        if task.run_at is None:
            raise ValueError(
                "One-time task is missing run_at"
            )

        run_at = task.run_at

        if run_at.tzinfo is None:
            run_at = run_at.replace(
                tzinfo=tz
            )

        return DateTrigger(
            run_date=run_at,
            timezone=tz,
        )

    if task.schedule_type == "daily":
        return CronTrigger(
            hour=task.hour,
            minute=task.minute,
            timezone=tz,
        )

    if task.schedule_type == "weekly":
        return CronTrigger(
            day_of_week=task.weekday,
            hour=task.hour,
            minute=task.minute,
            timezone=tz,
        )

    if task.schedule_type == "monthly":
        return CronTrigger(
            day=task.day_of_month,
            hour=task.hour,
            minute=task.minute,
            timezone=tz,
        )

    raise ValueError(
        f"Unsupported schedule type: {task.schedule_type}"
    )


def scheduler_job_id(
    task_id: int,
) -> str:
    return f"patchforge-task-{task_id}"


def schedule_task(
    task: ScheduledTask,
) -> None:
    job_id = scheduler_job_id(
        task.id
    )

    existing = scheduler.get_job(
        job_id
    )

    if existing is not None:
        scheduler.remove_job(
            job_id
        )

    if not task.enabled:
        task.next_run_at = None
        return

    trigger = build_trigger(
        task
    )

    job = scheduler.add_job(
        run_scheduled_task,
        trigger=trigger,
        args=[task.id],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    if job.next_run_time is not None:
        task.next_run_at = (
            job.next_run_time
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
    else:
        task.next_run_at = None


def remove_task_schedule(
    task_id: int,
) -> None:
    job_id = scheduler_job_id(
        task_id
    )

    existing = scheduler.get_job(
        job_id
    )

    if existing is not None:
        scheduler.remove_job(
            job_id
        )


def load_persistent_tasks() -> None:
    db = SessionLocal()

    try:
        tasks = list(
            db.scalars(
                select(ScheduledTask)
            ).all()
        )

        for task in tasks:
            if not task.enabled:
                task.next_run_at = None
                continue

            try:
                schedule_task(
                    task
                )

            except Exception:
                task.next_run_at = None

        db.commit()

    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()

    load_persistent_tasks()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(
            wait=False
        )
