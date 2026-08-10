from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.host_key import ServerHostKey
from app.models.server import Server
from app.models.task import ScheduledTask
from app.models.task_target import ScheduledTaskTarget
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate
from app.services.scheduler import remove_task_schedule


router = APIRouter(
    prefix="/api/servers",
    tags=["servers"],
)


@router.get(
    "",
    response_model=list[ServerResponse],
)
def list_servers(
    db: Session = Depends(get_db),
) -> list[Server]:
    return list(
        db.scalars(
            select(Server)
            .order_by(Server.name)
        ).all()
    )


@router.get(
    "/{server_id}",
    response_model=ServerResponse,
)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
) -> Server:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    return server


@router.post(
    "",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
) -> Server:
    server = Server(
        name=payload.name.strip(),
        host=payload.host.strip(),
        ssh_port=payload.ssh_port,
        username=payload.username.strip(),
    )

    db.add(server)
    db.commit()
    db.refresh(server)

    return server


@router.patch(
    "/{server_id}",
    response_model=ServerResponse,
)
def update_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
) -> Server:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    old_host = server.host
    old_port = server.ssh_port
    old_username = server.username

    if payload.name is not None:
        server.name = payload.name.strip()

    if payload.host is not None:
        server.host = payload.host.strip()

    if payload.ssh_port is not None:
        server.ssh_port = payload.ssh_port

    if payload.username is not None:
        server.username = payload.username.strip()

    connection_target_changed = (
        server.host != old_host
        or server.ssh_port != old_port
    )

    login_changed = (
        server.username != old_username
    )

    if connection_target_changed:
        db.execute(
            delete(ServerHostKey).where(
                ServerHostKey.server_id == server.id
            )
        )

        server.system_hostname = None
        server.distribution = None
        server.distribution_version = None
        server.package_manager = None
        server.architecture = None
        server.kernel_version = None
        server.reboot_required = False

    elif login_changed:
        # Host identity stays valid, but we want
        # discovery to be refreshed after saving.
        server.reboot_required = False

    db.commit()
    db.refresh(server)

    return server


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_server(
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

    tasks = list(
        db.scalars(
            select(ScheduledTask).where(
                ScheduledTask.id.in_(
                    select(
                        ScheduledTaskTarget.task_id
                    ).where(
                        ScheduledTaskTarget.server_id == server_id
                    )
                )
            )
        ).all()
    )

    for task in tasks:
        remove_task_schedule(
            task.id
        )

    db.execute(
        delete(ScheduledTaskTarget).where(
            ScheduledTaskTarget.server_id == server_id
        )
    )

    # A task without any remaining target is deleted.
    for task in tasks:
        remaining_target = db.scalar(
            select(ScheduledTaskTarget.id)
            .where(
                ScheduledTaskTarget.task_id == task.id
            )
            .limit(1)
        )

        if remaining_target is None:
            db.delete(task)

    db.execute(
        delete(ServerCredential).where(
            ServerCredential.server_id == server_id
        )
    )

    db.execute(
        delete(ServerHostKey).where(
            ServerHostKey.server_id == server_id
        )
    )

    db.delete(server)
    db.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
