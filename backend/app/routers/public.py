"""Endpoints reachable without an account: the visitor and delivery pass pages.

These serve a single record, addressed by an unguessable token, and expose only
what the holder already knows about their own visit.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.db import get_db
from app.deps import rate_limit_verification
from app.enums import CredentialStatus, SubjectType
from app.models import Delivery, Document, Employee, Visitor
from app.services import credentials as credential_service
from app.services import qr

router = APIRouter(prefix="/api/pass", tags=["pass"], dependencies=[Depends(rate_limit_verification)])


def _document_count(db: Session, subject_type: SubjectType, subject_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.subject_type == subject_type.value, Document.subject_id == subject_id
            )
        )
        or 0
    )


@router.get("/{token}", response_model=schemas.PassOut)
def view_pass(token: str, db: Session = Depends(get_db)):
    credential = credential_service.find_by_token(db, token)
    if not credential or credential.status != CredentialStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This pass is no longer available"
        )

    subject_type = SubjectType(credential.subject_type)
    qr_image = qr.qr_png_data_uri(qr.pass_url(subject_type, token))

    if subject_type is SubjectType.DELIVERY:
        delivery = db.get(Delivery, credential.subject_id)
        if not delivery:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pass not found")
        return schemas.PassOut(
            company_name=settings.company_name,
            pass_type=subject_type,
            reference=delivery.reference,
            holder_name=delivery.driver_name,
            organisation=delivery.company,
            vehicle_number=delivery.vehicle_number,
            purpose=delivery.purpose,
            purpose_description=delivery.purpose_description,
            gate_name=delivery.gate.name if delivery.gate else "",
            valid_from=delivery.valid_from,
            valid_until=delivery.valid_until,
            status=delivery.status,
            qr_image=qr_image,
            document_count=_document_count(db, subject_type, delivery.id),
        )

    if subject_type is SubjectType.VISITOR:
        visitor = db.get(Visitor, credential.subject_id)
        if not visitor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pass not found")
        return schemas.PassOut(
            company_name=settings.company_name,
            pass_type=subject_type,
            reference=visitor.reference,
            holder_name=visitor.full_name,
            organisation=visitor.company,
            purpose=visitor.purpose,
            purpose_description=visitor.purpose_description,
            gate_name=visitor.gate.name if visitor.gate else "",
            valid_from=visitor.valid_from,
            valid_until=visitor.valid_until,
            status=visitor.status,
            qr_image=qr_image,
            document_count=_document_count(db, subject_type, visitor.id),
        )

    employee = db.get(Employee, credential.subject_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pass not found")
    return schemas.PassOut(
        company_name=settings.company_name,
        pass_type=subject_type,
        reference=employee.employee_code,
        holder_name=employee.full_name,
        organisation=employee.department,
        purpose="EMPLOYEE_ACCESS",
        gate_name="As per access policy",
        valid_from=credential.valid_from or credential.created_at or datetime.utcnow(),
        valid_until=credential.valid_until or credential.created_at or datetime.utcnow(),
        status=employee.status,
        qr_image=qr_image,
    )
