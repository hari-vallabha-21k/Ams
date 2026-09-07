from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_gate_staff
from app.enums import DocumentType, SubjectType
from app.models import Delivery, Document, Employee, User, Visitor
from app.services import audit, storage

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _subject_or_404(db: Session, subject_type: SubjectType, subject_id: int) -> None:
    model = {
        SubjectType.EMPLOYEE: Employee,
        SubjectType.VISITOR: Visitor,
        SubjectType.DELIVERY: Delivery,
    }[subject_type]
    if not db.get(model, subject_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")


@router.post("/upload", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
def upload(
    request: Request,
    subject_type: SubjectType = Form(...),
    subject_id: int = Form(...),
    document_type: DocumentType = Form(DocumentType.INVOICE),
    reference_number: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    _subject_or_404(db, subject_type, subject_id)
    stored_path, size, file_name = storage.save_upload(file, subject_type.value, subject_id)
    document = Document(
        subject_type=subject_type.value,
        subject_id=subject_id,
        document_type=document_type.value,
        reference_number=reference_number,
        file_name=file_name,
        stored_path=stored_path,
        mime_type=file.content_type,
        size_bytes=size,
        uploaded_by=actor.id,
    )
    db.add(document)
    db.flush()
    audit.record(
        db,
        user=actor,
        action="UPLOAD_DOCUMENT",
        entity="document",
        entity_id=document.id,
        ip_address=client_ip(request),
        meta={
            "subject_type": subject_type.value,
            "subject_id": subject_id,
            "document_type": document_type.value,
            "reference_number": reference_number,
        },
    )
    db.commit()
    return document


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(
    subject_type: SubjectType,
    subject_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_gate_staff),
):
    return list(
        db.scalars(
            select(Document)
            .where(Document.subject_type == subject_type.value, Document.subject_id == subject_id)
            .order_by(Document.id)
        ).all()
    )


@router.get("/{document_id}", response_model=schemas.DocumentOut)
def get_document(
    document_id: int, db: Session = Depends(get_db), _: User = Depends(require_gate_staff)
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.get("/{document_id}/file")
def download_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_gate_staff),
):
    """Every view of a document is itself an audited event."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    audit.record(
        db,
        user=actor,
        action="VIEW_DOCUMENT",
        entity="document",
        entity_id=document.id,
        ip_address=client_ip(request),
        meta={"subject_type": document.subject_type, "subject_id": document.subject_id},
    )
    db.commit()
    return FileResponse(
        document.stored_path, media_type=document.mime_type, filename=document.file_name
    )
