from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.enums import (
    AccessStatus,
    CredentialStatus,
    DeliveryStatus,
    DenialReason,
    Direction,
    DocumentType,
    EmployeeStatus,
    GateStatus,
    Purpose,
    Role,
    SubjectType,
    VisitorStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth -------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    employee_id: int | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: Role
    password: str = Field(min_length=8, max_length=128)
    employee_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# --- employees --------------------------------------------------------------
class EmployeeBase(BaseModel):
    employee_code: str
    full_name: str
    photo_url: str | None = None
    department: str | None = None
    designation: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    date_joined: date | None = None


class EmployeeCreate(EmployeeBase):
    status: EmployeeStatus = EmployeeStatus.ACTIVE


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    photo_url: str | None = None
    department: str | None = None
    designation: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    date_joined: date | None = None
    status: EmployeeStatus | None = None


class EmployeeOut(EmployeeBase, ORMModel):
    id: int
    status: EmployeeStatus
    created_at: datetime | None = None


# --- gates ------------------------------------------------------------------
class GateCreate(BaseModel):
    code: str
    name: str
    location: str | None = None
    description: str | None = None
    status: GateStatus = GateStatus.ACTIVE


class GateUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    description: str | None = None
    status: GateStatus | None = None


class GateOut(ORMModel):
    id: int
    code: str
    name: str
    location: str | None = None
    description: str | None = None
    status: GateStatus


# --- access policies --------------------------------------------------------
class AccessPolicyCreate(BaseModel):
    employee_id: int
    gate_id: int
    valid_from: date
    valid_until: date
    days_of_week: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    start_time: time
    end_time: time
    is_active: bool = True

    @field_validator("days_of_week")
    @classmethod
    def _valid_days(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("At least one weekday is required")
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("Weekdays are 1 (Monday) to 7 (Sunday)")
        return sorted(set(value))

    @model_validator(mode="after")
    def _ranges(self):
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until must not be before valid_from")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AccessPolicyUpdate(BaseModel):
    valid_from: date | None = None
    valid_until: date | None = None
    days_of_week: list[int] | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None


class AccessPolicyOut(ORMModel):
    id: int
    employee_id: int
    gate_id: int
    gate: GateOut | None = None
    valid_from: date
    valid_until: date
    days_of_week: list[int]
    start_time: time
    end_time: time
    is_active: bool

    @field_validator("days_of_week", mode="before")
    @classmethod
    def _split_days(cls, value):
        if isinstance(value, str):
            return [int(d) for d in value.split(",") if d.strip()]
        return value


# --- credentials ------------------------------------------------------------
class CredentialOut(ORMModel):
    id: int
    subject_type: SubjectType
    subject_id: int
    status: CredentialStatus
    gate_id: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    created_at: datetime | None = None


class IssuedCredential(BaseModel):
    credential: CredentialOut
    token: str
    pass_url: str
    qr_image: str


class CredentialIssueRequest(BaseModel):
    subject_type: SubjectType
    subject_id: int


# --- visitors ---------------------------------------------------------------
class VisitorCreate(BaseModel):
    full_name: str
    company: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    host_employee_id: int | None = None
    purpose: Purpose
    purpose_description: str | None = None
    gate_id: int
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def _validate(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if self.purpose is Purpose.OTHER and not self.purpose_description:
            raise ValueError("purpose_description is required when purpose is OTHER")
        return self


class VisitorUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    host_employee_id: int | None = None
    purpose: Purpose | None = None
    purpose_description: str | None = None
    gate_id: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: VisitorStatus | None = None


class VisitorOut(ORMModel):
    id: int
    reference: str
    full_name: str
    company: str | None = None
    phone: str | None = None
    email: str | None = None
    host_employee_id: int | None = None
    host_name: str | None = None
    purpose: Purpose
    purpose_description: str | None = None
    gate_id: int
    gate_name: str | None = None
    valid_from: datetime
    valid_until: datetime
    status: VisitorStatus
    created_at: datetime | None = None


# --- deliveries -------------------------------------------------------------
class DeliveryCreate(BaseModel):
    company: str
    driver_name: str
    driver_phone: str | None = None
    vehicle_number: str | None = None
    purpose: Purpose = Purpose.MATERIAL_DELIVERY
    purpose_description: str | None = None
    host_department: str | None = None
    host_employee_id: int | None = None
    gate_id: int
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def _validate(self):
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if self.purpose is Purpose.OTHER and not self.purpose_description:
            raise ValueError("purpose_description is required when purpose is OTHER")
        return self


class DeliveryUpdate(BaseModel):
    company: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    vehicle_number: str | None = None
    purpose: Purpose | None = None
    purpose_description: str | None = None
    host_department: str | None = None
    host_employee_id: int | None = None
    gate_id: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: DeliveryStatus | None = None


class DeliveryOut(ORMModel):
    id: int
    reference: str
    company: str
    driver_name: str
    driver_phone: str | None = None
    vehicle_number: str | None = None
    purpose: Purpose
    purpose_description: str | None = None
    host_department: str | None = None
    host_employee_id: int | None = None
    host_name: str | None = None
    gate_id: int
    gate_name: str | None = None
    valid_from: datetime
    valid_until: datetime
    status: DeliveryStatus
    created_at: datetime | None = None


class PassOut(BaseModel):
    """What the driver or visitor sees when they open their pass link."""

    company_name: str
    pass_type: SubjectType
    reference: str
    holder_name: str
    organisation: str | None = None
    vehicle_number: str | None = None
    purpose: str
    purpose_description: str | None = None
    gate_name: str
    valid_from: datetime
    valid_until: datetime
    status: str
    qr_image: str
    document_count: int = 0


# --- documents --------------------------------------------------------------
class DocumentOut(ORMModel):
    id: int
    subject_type: SubjectType
    subject_id: int
    document_type: DocumentType
    reference_number: str | None = None
    file_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime | None = None


# --- verification -----------------------------------------------------------
class VerifyRequest(BaseModel):
    token: str
    gate_id: int
    direction: Direction = Direction.ENTRY


class CheckOut(BaseModel):
    code: str
    label: str
    passed: bool
    detail: str | None = None


class SubjectOut(BaseModel):
    type: SubjectType
    id: int | None = None
    label: str
    reference: str | None = None
    purpose: str | None = None
    purpose_description: str | None = None
    details: dict = Field(default_factory=dict)


class VerifyResponse(BaseModel):
    allowed: bool
    message: str
    direction: Direction
    gate: GateOut | None = None
    subject: SubjectOut | None = None
    checks: list[CheckOut]
    documents: list[DocumentOut] = Field(default_factory=list)
    suggested_denial_reason: DenialReason | None = None
    already_inside: bool = False


class DecisionRequest(BaseModel):
    token: str
    gate_id: int
    direction: Direction = Direction.ENTRY
    document_id: int | None = None


class DenyRequest(DecisionRequest):
    reason: DenialReason
    reason_note: str | None = None

    @model_validator(mode="after")
    def _note_required(self):
        if self.reason is DenialReason.OTHER and not self.reason_note:
            raise ValueError("reason_note is required when the reason is OTHER")
        return self


class AccessLogOut(ORMModel):
    id: int
    subject_type: SubjectType
    subject_id: int | None = None
    subject_label: str
    subject_reference: str | None = None
    gate_id: int | None = None
    gate_name: str | None = None
    direction: Direction | None = None
    status: AccessStatus
    reason: DenialReason | None = None
    reason_note: str | None = None
    purpose: str | None = None
    document_id: int | None = None
    verified_by: int | None = None
    verified_by_name: str | None = None
    occurred_at: datetime


class DecisionResponse(BaseModel):
    log: AccessLogOut
    verification: VerifyResponse


class PresenceOut(ORMModel):
    subject_type: SubjectType
    subject_id: int
    subject_label: str
    subject_reference: str | None = None
    purpose: str | None = None
    host_label: str | None = None
    gate_id: int | None = None
    gate_name: str | None = None
    entered_at: datetime
    expected_exit_at: datetime | None = None


class CurrentlyInside(BaseModel):
    total: int
    employees: int
    visitors: int
    delivery: int
    people: list[PresenceOut]


# --- dashboard / audit ------------------------------------------------------
class DashboardStats(BaseModel):
    employees: int
    visitors_today: int
    deliveries_today: int
    currently_inside: int
    denied_today: int
    granted_today: int
    recent_activity: list[AccessLogOut]
    active_gates: int


class AuditLogOut(ORMModel):
    id: int
    user_id: int | None = None
    user_label: str | None = None
    action: str
    entity: str
    entity_id: str | None = None
    ip_address: str | None = None
    meta: str | None = None
    created_at: datetime


class Page(BaseModel):
    total: int
    limit: int
    offset: int


class EmployeePage(Page):
    items: list[EmployeeOut]


class VisitorPage(Page):
    items: list[VisitorOut]


class DeliveryPage(Page):
    items: list[DeliveryOut]


class AccessLogPage(Page):
    items: list[AccessLogOut]


class AuditLogPage(Page):
    items: list[AuditLogOut]


TokenResponse.model_rebuild()
