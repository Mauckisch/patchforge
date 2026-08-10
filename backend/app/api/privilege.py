from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.server import Server
from app.services.discovery import (
    AuthenticationError,
    DiscoveryError,
)
from app.services.privilege import (
    PrivilegeError,
    PrivilegeUnavailableError,
    detect_privilege_method,
)


router = APIRouter(
    prefix="/api/servers",
    tags=["privilege"],
)


@router.post("/{server_id}/privilege-check")
def privilege_check(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = db.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    credential = db.scalar(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id
        )
    )

    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credentials configured",
        )

    ssh_password = decrypt_secret(
        credential.ssh_password_nonce,
        credential.ssh_password_ciphertext,
    )

    privilege_password = None

    if (
        credential.privilege_password_nonce is not None
        and credential.privilege_password_ciphertext is not None
    ):
        privilege_password = decrypt_secret(
            credential.privilege_password_nonce,
            credential.privilege_password_ciphertext,
        )

    try:
        return detect_privilege_method(
            host=server.host,
            port=server.ssh_port,
            username=server.username,
            ssh_password=ssh_password,
            configured_method=credential.privilege_method,
            privilege_password=privilege_password,
        )

    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except PrivilegeUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(exc),
                "diagnostics": exc.diagnostics,
            },
        ) from exc

    except (PrivilegeError, DiscoveryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
