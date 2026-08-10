from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import encrypt_secret
from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.server import Server
from app.schemas.credential import CredentialCreate, CredentialStatus


router = APIRouter(
    prefix="/api/servers",
    tags=["credentials"],
)


@router.get(
    "/{server_id}/credentials",
    response_model=CredentialStatus,
)
def get_credential_status(
    server_id: int,
    db: Session = Depends(get_db),
) -> CredentialStatus:
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
        return CredentialStatus(
            configured=False,
            privilege_method=None,
            separate_privilege_password=False,
        )

    return CredentialStatus(
        configured=True,
        privilege_method=credential.privilege_method,
        separate_privilege_password=(
            credential.privilege_password_ciphertext is not None
        ),
    )


@router.put(
    "/{server_id}/credentials",
    response_model=CredentialStatus,
)
def set_credentials(
    server_id: int,
    payload: CredentialCreate,
    db: Session = Depends(get_db),
) -> CredentialStatus:
    server = db.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    ssh_nonce, ssh_ciphertext = encrypt_secret(
        payload.ssh_password
    )

    privilege_nonce = None
    privilege_ciphertext = None

    if payload.privilege_password is not None:
        privilege_nonce, privilege_ciphertext = encrypt_secret(
            payload.privilege_password
        )

    credential = db.scalar(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id
        )
    )

    if credential is None:
        credential = ServerCredential(
            server_id=server_id,
            ssh_password_nonce=ssh_nonce,
            ssh_password_ciphertext=ssh_ciphertext,
            privilege_method=payload.privilege_method,
            privilege_password_nonce=privilege_nonce,
            privilege_password_ciphertext=privilege_ciphertext,
        )

        db.add(credential)

    else:
        credential.ssh_password_nonce = ssh_nonce
        credential.ssh_password_ciphertext = ssh_ciphertext
        credential.privilege_method = payload.privilege_method
        credential.privilege_password_nonce = privilege_nonce
        credential.privilege_password_ciphertext = privilege_ciphertext

    db.commit()

    return CredentialStatus(
        configured=True,
        privilege_method=payload.privilege_method,
        separate_privilege_password=(
            payload.privilege_password is not None
        ),
    )
