from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db
from app.deps import require_admin
from app.enums import (
    DenialReason,
    DocumentType,
    EmployeeStatus,
    Purpose,
    Role,
    SubjectType,
)
from app.routers import (
    access,
    auth,
    audit,
    credentials,
    dashboard,
    deliveries,
    documents,
    employees,
    gates,
    policies,
    public,
    reports,
    users,
    visitors,
)
from app.services import maintenance


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.bootstrap import initialise

    initialise()
    with SessionLocal() as db:
        maintenance.expire_passes(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Gate access, visitor and delivery management.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url, "http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(employees.router)
app.include_router(gates.router)
app.include_router(policies.router)
app.include_router(visitors.router)
app.include_router(deliveries.router)
app.include_router(credentials.router)
app.include_router(documents.router)
app.include_router(access.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(public.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/meta", tags=["system"])
def meta():
    """Reference data the UI needs for its dropdowns."""
    return {
        "company_name": settings.company_name,
        "roles": [r.value for r in Role],
        "purposes": [p.value for p in Purpose],
        "denial_reasons": [d.value for d in DenialReason],
        "document_types": [d.value for d in DocumentType],
        "employee_statuses": [s.value for s in EmployeeStatus],
        "subject_types": [s.value for s in SubjectType],
    }


@app.post("/api/maintenance/expire-passes", tags=["system"])
def expire_passes(db: Session = Depends(get_db), _=Depends(require_admin)):
    return maintenance.expire_passes(db)
