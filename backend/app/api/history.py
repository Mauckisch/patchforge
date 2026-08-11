from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.history import HistoryEntry
from app.models.server import Server
from app.models.task_run import (
    TaskRun,
    TaskRunResult,
)
from app.schemas.history import (
    HistoryResponse,
    TaskRunHistoryResponse,
)


router = APIRouter(
    tags=["history"],
)


@router.get(
    "/api/history",
    response_model=list[HistoryResponse],
)
def get_history(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[HistoryEntry]:
    limit = max(
        1,
        min(limit, 500),
    )

    return list(
        db.scalars(
            select(HistoryEntry)
            .where(
                HistoryEntry.task_run_id.is_(None)
            )
            .order_by(
                HistoryEntry.created_at.desc()
            )
            .limit(limit)
        ).all()
    )


@router.get(
    "/api/history/task-runs",
    response_model=list[TaskRunHistoryResponse],
)
def get_task_run_history(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[TaskRun]:
    limit = max(
        1,
        min(limit, 500),
    )

    return list(
        db.scalars(
            select(TaskRun)
            .where(
                TaskRun.status != "RUNNING"
            )
            .order_by(
                TaskRun.started_at.desc()
            )
            .limit(limit)
        ).all()
    )


@router.delete(
    "/api/history",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_history(
    db: Session = Depends(get_db),
) -> Response:
    db.execute(
        delete(HistoryEntry)
    )

    db.execute(
        delete(TaskRunResult)
    )

    db.execute(
        delete(TaskRun)
    )

    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/api/servers/{server_id}/history",
    response_model=list[HistoryResponse],
)
def get_server_history(
    server_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[HistoryEntry]:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    limit = max(
        1,
        min(limit, 500),
    )

    return list(
        db.scalars(
            select(HistoryEntry)
            .where(
                HistoryEntry.server_id == server_id
            )
            .order_by(
                HistoryEntry.created_at.desc()
            )
            .limit(limit)
        ).all()
    )


@router.delete(
    "/api/servers/{server_id}/history",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_server_history(
    server_id: int,
    db: Session = Depends(get_db),
) -> Response:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    db.execute(
        delete(HistoryEntry).where(
            HistoryEntry.server_id == server_id
        )
    )

    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
