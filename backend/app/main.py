from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.credentials import router as credentials_router
from app.api.discovery import router as discovery_router
from app.api.history import router as history_router
from app.api.notifications import router as notifications_router
from app.api.privilege import router as privilege_router
from app.api.servers import router as servers_router
from app.api.settings import router as settings_router
from app.api.status import router as status_router
from app.api.tasks import router as tasks_router
from app.api.updates import router as updates_router
from app.core.database import (
    Base,
    engine,
    run_database_migrations,
)
from app.models.credential import ServerCredential
from app.models.history import HistoryEntry
from app.models.host_key import ServerHostKey
from app.models.server import Server
from app.models.server_update import ServerUpdate
from app.models.server_update_lock import ServerUpdateLock
from app.models.settings import AppSettings
from app.models.notification import (
    NotificationEventPreference,
    NotificationSettings,
)
from app.models.task import ScheduledTask
from app.models.task_run import (
    TaskRun,
    TaskRunResult,
)
from app.models.task_target import ScheduledTaskTarget
from app.services.scheduler import (
    start_scheduler,
    stop_scheduler,
)


Base.metadata.create_all(
    bind=engine
)

run_database_migrations()

FRONTEND_DIR = Path(
    "/app/frontend"
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    start_scheduler()

    yield

    stop_scheduler()


app = FastAPI(
    title="PatchForge for Linux",
    version="1.5.1",
    lifespan=lifespan,
)

app.include_router(servers_router)
app.include_router(credentials_router)
app.include_router(discovery_router)
app.include_router(privilege_router)
app.include_router(updates_router)
app.include_router(history_router)
app.include_router(notifications_router)
app.include_router(tasks_router)
app.include_router(settings_router)
app.include_router(status_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "PatchForge for Linux",
        "version": "1.5.1",
    }


if FRONTEND_DIR.exists():
    assets_dir = FRONTEND_DIR / "assets"

    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(
                directory=assets_dir
            ),
            name="assets",
        )

    branding_dir = FRONTEND_DIR / "branding"

    if branding_dir.exists():
        app.mount(
            "/branding",
            StaticFiles(
                directory=branding_dir
            ),
            name="branding",
        )


@app.get("/")
def frontend_index():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/{path:path}")
def frontend_fallback(
    path: str,
):
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )
