from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.server import Server
from app.models.task import ScheduledTask
from app.models.task_target import ScheduledTaskTarget
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.scheduler import (
    remove_task_schedule,
    schedule_task,
    validate_timezone,
)
from app.services.task_runner import run_scheduled_task


router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
)


def _server_ids(
    db: Session,
    task_id: int,
) -> list[int]:
    return list(
        db.scalars(
            select(
                ScheduledTaskTarget.server_id
            )
            .where(
                ScheduledTaskTarget.task_id == task_id
            )
            .order_by(
                ScheduledTaskTarget.server_id
            )
        ).all()
    )


def _response(
    db: Session,
    task: ScheduledTask,
) -> dict:
    return {
        "id": task.id,
        "name": task.name,
        "server_ids": _server_ids(
            db,
            task.id,
        ),
        "action": task.action,
        "schedule_type": task.schedule_type,
        "timezone": task.timezone,
        "run_at": task.run_at,
        "hour": task.hour,
        "minute": task.minute,
        "weekday": task.weekday,
        "day_of_month": task.day_of_month,
        "enabled": task.enabled,
        "last_run_at": task.last_run_at,
        "next_run_at": task.next_run_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _validate_servers(
    db: Session,
    server_ids: list[int],
) -> None:
    found_ids = set(
        db.scalars(
            select(Server.id).where(
                Server.id.in_(server_ids)
            )
        ).all()
    )

    missing_ids = [
        server_id
        for server_id in server_ids
        if server_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Server not found: "
                + ", ".join(
                    str(server_id)
                    for server_id in missing_ids
                )
            ),
        )


def _validate_task_schedule(
    payload: TaskCreate | TaskUpdate,
) -> None:
    try:
        validate_timezone(
            payload.timezone
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if payload.schedule_type != "once":
        return

    run_at = payload.run_at

    if run_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="run_at is required",
        )

    if run_at.tzinfo is None:
        tz = validate_timezone(
            payload.timezone
        )

        run_at_aware = run_at.replace(
            tzinfo=tz
        )

    else:
        run_at_aware = run_at

    if run_at_aware <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="run_at must be in the future",
        )


def _replace_targets(
    db: Session,
    task_id: int,
    server_ids: list[int],
) -> None:
    db.execute(
        delete(ScheduledTaskTarget).where(
            ScheduledTaskTarget.task_id == task_id
        )
    )

    for server_id in server_ids:
        db.add(
            ScheduledTaskTarget(
                task_id=task_id,
                server_id=server_id,
            )
        )


@router.get(
    "",
    response_model=list[TaskResponse],
)
def list_tasks(
    db: Session = Depends(get_db),
) -> list[dict]:
    tasks = list(
        db.scalars(
            select(ScheduledTask)
            .order_by(
                ScheduledTask.created_at.desc()
            )
        ).all()
    )

    return [
        _response(db, task)
        for task in tasks
    ]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
) -> dict:
    task = db.get(
        ScheduledTask,
        task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return _response(
        db,
        task,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
) -> dict:
    _validate_servers(
        db,
        payload.server_ids,
    )

    _validate_task_schedule(
        payload
    )

    task = ScheduledTask(
        name=payload.name.strip(),

        # Legacy compatibility only.
        server_id=payload.server_ids[0],

        action=payload.action,
        schedule_type=payload.schedule_type,
        timezone=payload.timezone,
        run_at=payload.run_at,
        hour=payload.hour,
        minute=payload.minute,
        weekday=payload.weekday,
        day_of_month=payload.day_of_month,
        enabled=payload.enabled,
    )

    db.add(task)
    db.flush()

    _replace_targets(
        db,
        task.id,
        payload.server_ids,
    )

    db.commit()
    db.refresh(task)

    try:
        schedule_task(
            task
        )

        db.commit()
        db.refresh(task)

    except Exception as exc:
        db.execute(
            delete(ScheduledTaskTarget).where(
                ScheduledTaskTarget.task_id == task.id
            )
        )

        db.delete(task)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to schedule task: {exc}",
        ) from exc

    return _response(
        db,
        task,
    )


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
) -> dict:
    task = db.get(
        ScheduledTask,
        task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    _validate_servers(
        db,
        payload.server_ids,
    )

    _validate_task_schedule(
        payload
    )

    task.name = payload.name.strip()

    # Legacy compatibility only.
    task.server_id = payload.server_ids[0]

    task.action = payload.action
    task.schedule_type = payload.schedule_type
    task.timezone = payload.timezone

    task.run_at = (
        payload.run_at
        if payload.schedule_type == "once"
        else None
    )

    task.hour = (
        payload.hour
        if payload.schedule_type != "once"
        else None
    )

    task.minute = (
        payload.minute
        if payload.schedule_type != "once"
        else None
    )

    task.weekday = (
        payload.weekday
        if payload.schedule_type == "weekly"
        else None
    )

    task.day_of_month = (
        payload.day_of_month
        if payload.schedule_type == "monthly"
        else None
    )

    task.enabled = payload.enabled

    _replace_targets(
        db,
        task.id,
        payload.server_ids,
    )

    try:
        schedule_task(
            task
        )

        db.commit()
        db.refresh(task)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to reschedule task: {exc}",
        ) from exc

    return _response(
        db,
        task,
    )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
) -> Response:
    task = db.get(
        ScheduledTask,
        task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    remove_task_schedule(
        task.id
    )

    db.execute(
        delete(ScheduledTaskTarget).where(
            ScheduledTaskTarget.task_id == task.id
        )
    )

    db.delete(task)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.post("/{task_id}/run")
def run_task_now(
    task_id: int,
    db: Session = Depends(get_db),
) -> dict:
    task = db.get(
        ScheduledTask,
        task_id,
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    run_scheduled_task(
        task.id
    )

    db.expire_all()

    task = db.get(
        ScheduledTask,
        task_id,
    )

    return {
        "task_id": task.id,
        "name": task.name,
        "action": task.action,
        "last_run_at": task.last_run_at,
        "next_run_at": task.next_run_at,
        "enabled": task.enabled,
    }
