from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user, require_admin
from app.enums import Role, SubjectType
from app.models import Delivery, Employee, User, Visitor
from app.services import audit
from app.services import credentials as credential_service

router = APIRouter(prefix="/api/qr", tags=["credentials"])


def _subject_exists(db: Session, subject_type: SubjectType, subject_id: int) -> bool:
    model = {
        SubjectType.EMPLOYEE: Employee,
        SubjectType.VISITOR: Visitor,
        SubjectType.DELIVERY: Delivery,
    }[subject_type]
    return db.get(model, subject_id) is not None


def _issued(credential, token: str) -> schemas.IssuedCredential:
    payload = credential_service.credential_payload(SubjectType(credential.subject_type), token)
    return schemas.IssuedCredential(
        credential=schemas.CredentialOut.model_validate(credential), **payload
    )


@router.post("/generate", response_model=schemas.IssuedCredential, status_code=status.HTTP_201_CREATED)
def generate(
    payload: schemas.CredentialIssueRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Issue (or re-issue) a credential. Any previous one is revoked."""
    if not _subject_exists(db, payload.subject_type, payload.subject_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    gate_id = None
    valid_from = valid_until = None
    if payload.subject_type is SubjectType.VISITOR:
        visitor = db.get(Visitor, payload.subject_id)
        gate_id, valid_from, valid_until = visitor.gate_id, visitor.valid_from, visitor.valid_until
    elif payload.subject_type is SubjectType.DELIVERY:
        delivery = db.get(Delivery, payload.subject_id)
        gate_id, valid_from, valid_until = delivery.gate_id, delivery.valid_from, delivery.valid_until

    credential, token = credential_service.issue(
        db,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        gate_id=gate_id,
        valid_from=valid_from,
        valid_until=valid_until,
        issued_by=actor,
    )
    audit.record(
        db,
        user=actor,
        action="GENERATE_QR",
        entity="qr_credential",
        entity_id=credential.id,
        ip_address=client_ip(request),
        meta={"subject_type": payload.subject_type.value, "subject_id": payload.subject_id},
    )
    db.commit()
    return _issued(credential, token)


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke(
    payload: schemas.CredentialIssueRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    revoked = credential_service.revoke_existing(db, payload.subject_type, payload.subject_id)
    if revoked == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active credential to revoke")
    audit.record(
        db,
        user=actor,
        action="REVOKE_QR",
        entity="qr_credential",
        entity_id=f"{payload.subject_type.value}:{payload.subject_id}",
        ip_address=client_ip(request),
    )
    db.commit()


@router.get("/subject/{subject_type}/{subject_id}", response_model=schemas.IssuedCredential)
def current_credential(
    subject_type: SubjectType,
    subject_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Show the live credential again - for reprinting or re-sharing a pass."""
    if user.role == Role.EMPLOYEE.value and not (
        subject_type is SubjectType.EMPLOYEE and user.employee_id == subject_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    if user.role == Role.SECURITY_GUARD.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    credential = credential_service.active_credential(db, subject_type, subject_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active credential")
    token = credential_service.plaintext_token(credential)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored credential cannot be decrypted; re-issue the QR",
        )
    return _issued(credential, token)


@router.get("/me", response_model=schemas.IssuedCredential)
def my_credential(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The employee portal QR."""
    if not user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This account is not linked to an employee"
        )
    credential = credential_service.active_credential(db, SubjectType.EMPLOYEE, user.employee_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active credential")
    token = credential_service.plaintext_token(credential)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored credential cannot be decrypted; ask an administrator to re-issue it",
        )
    return _issued(credential, token)
