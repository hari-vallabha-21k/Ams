import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import client_ip, require_admin
from app.enums import AccessStatus, SubjectType
from app.models import AccessLog, Delivery, Gate, Presence, User, Visitor
from app.services import audit, reporting

router = APIRouter(prefix="/api/reports", tags=["reports"])

Format = Query("json", pattern="^(json|csv|pdf)$")


def _range(date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
    end = date_to or datetime.utcnow().date()
    start = date_from or end
    return datetime.combine(start, time.min), datetime.combine(end, time.max)


def _render(
    request: Request,
    db: Session,
    actor: User,
    *,
    name: str,
    title: str,
    headers: list[str],
    rows: list[list],
    fmt: str,
) -> Response:
    audit.record(
        db,
        user=actor,
        action="GENERATE_REPORT",
        entity="report",
        entity_id=name,
        ip_address=client_ip(request),
        meta={"format": fmt, "rows": len(rows)},
    )
    db.commit()
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    if fmt == "csv":
        return Response(
            content=reporting.to_csv(headers, rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.csv"'},
        )
    if fmt == "pdf":
        return Response(
            content=reporting.to_pdf(title, headers, rows),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.pdf"'},
        )
    return JSONResponse(
        json.loads(
            json.dumps(
                {
                    "title": title,
                    "headers": headers,
                    "rows": [[str(v) if v is not None else "" for v in row] for row in rows],
                }
            )
        )
    )


@router.get("/access")
def access_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    gate_id: int | None = None,
    subject_type: SubjectType | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    start, end = _range(date_from, date_to)
    query = select(AccessLog).where(AccessLog.occurred_at.between(start, end))
    if gate_id:
        query = query.where(AccessLog.gate_id == gate_id)
    if subject_type:
        query = query.where(AccessLog.subject_type == subject_type.value)
    logs = db.scalars(query.order_by(AccessLog.occurred_at)).all()
    headers = ["Time", "Type", "Reference", "Person", "Gate", "Direction", "Status", "Purpose", "Reason"]
    rows = [
        [
            f"{log.occurred_at:%d/%m/%Y %H:%M}",
            log.subject_type,
            log.subject_reference,
            log.subject_label,
            log.gate.name if log.gate else "",
            log.direction or "",
            log.status,
            log.purpose or "",
            log.reason or "",
        ]
        for log in logs
    ]
    return _render(
        request, db, actor, name="access-report", title="Access Report", headers=headers, rows=rows, fmt=format
    )


@router.get("/deliveries")
def delivery_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    start, end = _range(date_from, date_to)
    deliveries = db.scalars(
        select(Delivery).where(Delivery.valid_from.between(start, end)).order_by(Delivery.valid_from)
    ).all()
    headers = ["Reference", "Company", "Driver", "Vehicle", "Purpose", "Gate", "Valid from", "Valid until", "Status"]
    rows = [
        [
            d.reference,
            d.company,
            d.driver_name,
            d.vehicle_number,
            d.purpose,
            d.gate.name if d.gate else "",
            f"{d.valid_from:%d/%m/%Y %H:%M}",
            f"{d.valid_until:%d/%m/%Y %H:%M}",
            d.status,
        ]
        for d in deliveries
    ]
    return _render(
        request, db, actor, name="delivery-report", title="Delivery Report", headers=headers, rows=rows, fmt=format
    )


@router.get("/visitors")
def visitor_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    start, end = _range(date_from, date_to)
    visitors = db.scalars(
        select(Visitor).where(Visitor.valid_from.between(start, end)).order_by(Visitor.valid_from)
    ).all()
    headers = ["Reference", "Visitor", "Company", "Host", "Purpose", "Gate", "Valid from", "Valid until", "Status"]
    rows = [
        [
            v.reference,
            v.full_name,
            v.company,
            v.host.full_name if v.host else "",
            v.purpose,
            v.gate.name if v.gate else "",
            f"{v.valid_from:%d/%m/%Y %H:%M}",
            f"{v.valid_until:%d/%m/%Y %H:%M}",
            v.status,
        ]
        for v in visitors
    ]
    return _render(
        request, db, actor, name="visitor-report", title="Visitor Report", headers=headers, rows=rows, fmt=format
    )


@router.get("/denied")
def denied_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    start, end = _range(date_from, date_to)
    logs = db.scalars(
        select(AccessLog)
        .where(AccessLog.status == AccessStatus.DENIED.value, AccessLog.occurred_at.between(start, end))
        .order_by(AccessLog.occurred_at)
    ).all()
    headers = ["Time", "Type", "Reference", "Person", "Gate", "Reason", "Note"]
    rows = [
        [
            f"{log.occurred_at:%d/%m/%Y %H:%M}",
            log.subject_type,
            log.subject_reference,
            log.subject_label,
            log.gate.name if log.gate else "",
            log.reason or "",
            log.reason_note or "",
        ]
        for log in logs
    ]
    return _render(
        request, db, actor, name="denied-access-report", title="Denied Access Report", headers=headers, rows=rows, fmt=format
    )


@router.get("/gate-wise")
def gate_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    start, end = _range(date_from, date_to)
    counts = dict(
        db.execute(
            select(AccessLog.gate_id, func.count())
            .where(AccessLog.occurred_at.between(start, end))
            .group_by(AccessLog.gate_id)
        ).all()
    )
    granted = dict(
        db.execute(
            select(AccessLog.gate_id, func.count())
            .where(
                AccessLog.occurred_at.between(start, end),
                AccessLog.status == AccessStatus.GRANTED.value,
            )
            .group_by(AccessLog.gate_id)
        ).all()
    )
    gates = db.scalars(select(Gate).order_by(Gate.id)).all()
    headers = ["Gate", "Location", "Status", "Total attempts", "Granted", "Denied"]
    rows = [
        [
            gate.name,
            gate.location or "",
            gate.status,
            counts.get(gate.id, 0),
            granted.get(gate.id, 0),
            counts.get(gate.id, 0) - granted.get(gate.id, 0),
        ]
        for gate in gates
    ]
    return _render(
        request, db, actor, name="gate-report", title="Gate-wise Access Report", headers=headers, rows=rows, fmt=format
    )


@router.get("/currently-inside")
def inside_report(
    request: Request,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Doubles as the evacuation list."""
    people = db.scalars(select(Presence).order_by(Presence.entered_at)).all()
    headers = ["Type", "Reference", "Name", "Purpose", "Host", "Gate", "Entered at", "Expected exit"]
    rows = [
        [
            p.subject_type,
            p.subject_reference or "",
            p.subject_label,
            p.purpose or "",
            p.host_label or "",
            p.gate.name if p.gate else "",
            f"{p.entered_at:%d/%m/%Y %H:%M}",
            f"{p.expected_exit_at:%d/%m/%Y %H:%M}" if p.expected_exit_at else "",
        ]
        for p in people
    ]
    return _render(
        request, db, actor, name="currently-inside", title="People Currently Inside", headers=headers, rows=rows, fmt=format
    )


@router.get("/entry-exit")
def entry_exit_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    format: str = Format,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    """Entry and exit paired per person per day, with time on site."""
    start, end = _range(date_from, date_to)
    logs = db.scalars(
        select(AccessLog)
        .where(
            AccessLog.status == AccessStatus.GRANTED.value,
            AccessLog.occurred_at.between(start, end),
        )
        .order_by(AccessLog.occurred_at)
    ).all()
    open_entries: dict[tuple[str, int | None], AccessLog] = {}
    rows: list[list] = []
    for log in logs:
        key = (log.subject_type, log.subject_id)
        if log.direction == "ENTRY":
            open_entries[key] = log
        elif log.direction == "EXIT":
            entry = open_entries.pop(key, None)
            duration = (
                str(timedelta(seconds=int((log.occurred_at - entry.occurred_at).total_seconds())))
                if entry
                else ""
            )
            rows.append(
                [
                    log.subject_type,
                    log.subject_reference or "",
                    log.subject_label,
                    f"{entry.occurred_at:%d/%m/%Y %H:%M}" if entry else "",
                    f"{log.occurred_at:%d/%m/%Y %H:%M}",
                    duration,
                    log.gate.name if log.gate else "",
                ]
            )
    for entry in open_entries.values():
        rows.append(
            [
                entry.subject_type,
                entry.subject_reference or "",
                entry.subject_label,
                f"{entry.occurred_at:%d/%m/%Y %H:%M}",
                "still inside",
                "",
                entry.gate.name if entry.gate else "",
            ]
        )
    headers = ["Type", "Reference", "Person", "Entry", "Exit", "Time on site", "Gate"]
    return _render(
        request, db, actor, name="entry-exit-report", title="Entry / Exit Report", headers=headers, rows=rows, fmt=format
    )
