from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = "sqlite:////data/patchforge.db"


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def _columns(
    connection,
    table: str,
) -> set[str]:
    return {
        column[1]
        for column in connection.execute(
            text(
                f"PRAGMA table_info({table})"
            )
        ).fetchall()
    }


def run_database_migrations() -> None:
    with engine.begin() as connection:
        server_columns = _columns(
            connection,
            "servers",
        )

        migrations = {
            "system_hostname":
                "ALTER TABLE servers "
                "ADD COLUMN system_hostname VARCHAR(255)",

            "connection_status":
                "ALTER TABLE servers "
                "ADD COLUMN connection_status VARCHAR(30) "
                "NOT NULL DEFAULT 'UNKNOWN'",

            "updates_available":
                "ALTER TABLE servers "
                "ADD COLUMN updates_available INTEGER "
                "NOT NULL DEFAULT 0",

            "last_seen_at":
                "ALTER TABLE servers "
                "ADD COLUMN last_seen_at DATETIME",

            "updates_checked_at":
                "ALTER TABLE servers "
                "ADD COLUMN updates_checked_at DATETIME",

            "last_check_at":
                "ALTER TABLE servers "
                "ADD COLUMN last_check_at DATETIME",

            "last_error":
                "ALTER TABLE servers "
                "ADD COLUMN last_error TEXT",
        }

        for column, statement in migrations.items():
            if column not in server_columns:
                connection.execute(
                    text(statement)
                )

        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table'"
                )
            )
        }

        if "server_updates" in tables:
            update_columns = _columns(
                connection,
                "server_updates",
            )

            if "held" not in update_columns:
                connection.execute(
                    text(
                        "ALTER TABLE server_updates "
                        "ADD COLUMN held BOOLEAN "
                        "NOT NULL DEFAULT 0"
                    )
                )

        if (
            "scheduled_tasks" in tables
            and "scheduled_task_targets" in tables
        ):
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO scheduled_task_targets
                        (task_id, server_id)
                    SELECT id, server_id
                    FROM scheduled_tasks
                    WHERE server_id IS NOT NULL
                    """
                )
            )
