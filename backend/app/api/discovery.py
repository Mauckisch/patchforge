from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.host_key import ServerHostKey
from app.models.server import Server
from app.schemas.server import ServerResponse
from app.services.discovery import (
    AuthenticationError,
    DiscoveryError,
    HostKeyMismatchError,
    UnsupportedDistributionError,
    discover_server,
)


router = APIRouter(
    prefix="/api/servers",
    tags=["discovery"],
)


@router.post(
    "/{server_id}/discover",
    response_model=ServerResponse,
)
def discover(
    server_id: int,
    db: Session = Depends(get_db),
) -> Server:
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

    host_key = db.scalar(
        select(ServerHostKey).where(
            ServerHostKey.server_id == server_id
        )
    )

    password = decrypt_secret(
        credential.ssh_password_nonce,
        credential.ssh_password_ciphertext,
    )

    try:
        result = discover_server(
            host=server.host,
            port=server.ssh_port,
            username=server.username,
            password=password,
            expected_host_key=(
                host_key.fingerprint
                if host_key is not None
                else None
            ),
        )

    except HostKeyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    except UnsupportedDistributionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except DiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if host_key is None:
        host_key = ServerHostKey(
            server_id=server.id,
            fingerprint=result.host_key_fingerprint,
        )

        db.add(host_key)

    server.system_hostname = result.hostname
    server.distribution = result.distribution
    server.distribution_version = result.distribution_version
    server.package_manager = result.package_manager
    server.architecture = result.architecture
    server.kernel_version = result.kernel_version

    db.commit()
    db.refresh(server)

    return server
