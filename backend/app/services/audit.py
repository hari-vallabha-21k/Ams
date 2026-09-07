import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity: str,
    entity_id: Any = None,
    ip_address: str | None = None,
    meta: dict | None = None,
) -> AuditLog:
    """Append an administrative action to the audit trail.

    The caller is responsible for committing; the entry takes part in the same
    transaction as the action it describes.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        user_label=f"{user.full_name} <{user.email}>" if user else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        meta=json.dumps(meta, default=str) if meta else None,
    )
    db.add(entry)
    return entry
