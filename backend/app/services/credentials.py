from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import CredentialStatus, SubjectType
from app.models import QrCredential, User
from app.security import decrypt_token, encrypt_token, generate_token, hash_token
from app.services import qr


def active_credential(
    db: Session, subject_type: SubjectType, subject_id: int
) -> QrCredential | None:
    return db.scalars(
        select(QrCredential)
        .where(
            QrCredential.subject_type == subject_type.value,
            QrCredential.subject_id == subject_id,
            QrCredential.status == CredentialStatus.ACTIVE.value,
        )
        .order_by(QrCredential.id.desc())
    ).first()


def revoke_existing(db: Session, subject_type: SubjectType, subject_id: int) -> int:
    """Revoke every live credential for a subject. Returns how many were revoked."""
    credentials = db.scalars(
        select(QrCredential).where(
            QrCredential.subject_type == subject_type.value,
            QrCredential.subject_id == subject_id,
            QrCredential.status == CredentialStatus.ACTIVE.value,
        )
    ).all()
    for credential in credentials:
        credential.status = CredentialStatus.REVOKED.value
        credential.revoked_at = datetime.utcnow()
    return len(credentials)


def issue(
    db: Session,
    *,
    subject_type: SubjectType,
    subject_id: int,
    gate_id: int | None = None,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    issued_by: User | None = None,
    replace: bool = True,
) -> tuple[QrCredential, str]:
    """Issue a credential and return it together with the one-time plaintext token.

    The plaintext token is never stored; only its SHA-256 hash is persisted, so
    the token can only be handed out at issue time.
    """
    if replace:
        revoke_existing(db, subject_type, subject_id)
    token = generate_token()
    credential = QrCredential(
        subject_type=subject_type.value,
        subject_id=subject_id,
        token_hash=hash_token(token),
        token_encrypted=encrypt_token(token),
        status=CredentialStatus.ACTIVE.value,
        gate_id=gate_id,
        valid_from=valid_from,
        valid_until=valid_until,
        issued_by=issued_by.id if issued_by else None,
    )
    db.add(credential)
    db.flush()
    return credential, token


def credential_payload(subject_type: SubjectType, token: str) -> dict:
    url = qr.pass_url(subject_type, token)
    return {"token": token, "pass_url": url, "qr_image": qr.qr_png_data_uri(url)}


def find_by_token(db: Session, token: str) -> QrCredential | None:
    return db.scalars(
        select(QrCredential).where(QrCredential.token_hash == hash_token(token))
    ).first()


def plaintext_token(credential: QrCredential) -> str | None:
    """Recover the token so an existing pass can be shown again to its owner."""
    return decrypt_token(credential.token_encrypted)
