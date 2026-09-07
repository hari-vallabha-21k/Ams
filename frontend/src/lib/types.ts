export type Role = "SUPER_ADMIN" | "ADMIN" | "SECURITY_GUARD" | "EMPLOYEE";
export type SubjectType = "EMPLOYEE" | "VISITOR" | "DELIVERY";
export type Direction = "ENTRY" | "EXIT";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  employee_id: number | null;
}

export interface Gate {
  id: number;
  code: string;
  name: string;
  location: string | null;
  description: string | null;
  status: "ACTIVE" | "INACTIVE";
}

export interface Employee {
  id: number;
  employee_code: string;
  full_name: string;
  department: string | null;
  designation: string | null;
  phone: string | null;
  email: string | null;
  photo_url: string | null;
  date_joined: string | null;
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
}

export interface AccessPolicy {
  id: number;
  employee_id: number;
  gate_id: number;
  valid_from: string;
  valid_until: string;
  days_of_week: number[];
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export interface Visitor {
  id: number;
  reference: string;
  full_name: string;
  company: string | null;
  phone: string | null;
  email: string | null;
  host_employee_id: number | null;
  host_name: string | null;
  purpose: string;
  purpose_description: string | null;
  gate_id: number;
  gate_name: string | null;
  valid_from: string;
  valid_until: string;
  status: string;
}

export interface Delivery {
  id: number;
  reference: string;
  company: string;
  driver_name: string;
  driver_phone: string | null;
  vehicle_number: string | null;
  purpose: string;
  purpose_description: string | null;
  host_department: string | null;
  host_employee_id: number | null;
  host_name: string | null;
  gate_id: number;
  gate_name: string | null;
  valid_from: string;
  valid_until: string;
  status: string;
}

export interface IssuedCredential {
  credential: {
    id: number;
    subject_type: SubjectType;
    subject_id: number;
    status: string;
    valid_from: string | null;
    valid_until: string | null;
  };
  token: string;
  pass_url: string;
  qr_image: string;
}

export interface DocumentRecord {
  id: number;
  subject_type: SubjectType;
  subject_id: number;
  document_type: string;
  reference_number: string | null;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string | null;
}

export interface Check {
  code: string;
  label: string;
  passed: boolean;
  detail: string | null;
}

export interface Verification {
  allowed: boolean;
  message: string;
  direction: Direction;
  gate: Gate | null;
  subject: {
    type: SubjectType;
    id: number | null;
    label: string;
    reference: string | null;
    purpose: string | null;
    purpose_description: string | null;
    details: Record<string, string | null>;
  } | null;
  checks: Check[];
  documents: DocumentRecord[];
  suggested_denial_reason: string | null;
  already_inside: boolean;
}

export interface AccessLog {
  id: number;
  subject_type: SubjectType;
  subject_id: number | null;
  subject_label: string;
  subject_reference: string | null;
  gate_id: number | null;
  gate_name: string | null;
  direction: Direction | null;
  status: "GRANTED" | "DENIED";
  reason: string | null;
  reason_note: string | null;
  purpose: string | null;
  verified_by_name: string | null;
  occurred_at: string;
}

export interface PresenceRecord {
  subject_type: SubjectType;
  subject_id: number;
  subject_label: string;
  subject_reference: string | null;
  purpose: string | null;
  host_label: string | null;
  gate_name: string | null;
  entered_at: string;
  expected_exit_at: string | null;
}

export interface CurrentlyInside {
  total: number;
  employees: number;
  visitors: number;
  delivery: number;
  people: PresenceRecord[];
}

export interface DashboardStats {
  employees: number;
  visitors_today: number;
  deliveries_today: number;
  currently_inside: number;
  denied_today: number;
  granted_today: number;
  active_gates: number;
  recent_activity: AccessLog[];
}

export interface AuditEntry {
  id: number;
  user_label: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  ip_address: string | null;
  meta: string | null;
  created_at: string;
}

export interface PassView {
  company_name: string;
  pass_type: SubjectType;
  reference: string;
  holder_name: string;
  organisation: string | null;
  vehicle_number: string | null;
  purpose: string;
  purpose_description: string | null;
  gate_name: string;
  valid_from: string;
  valid_until: string;
  status: string;
  qr_image: string;
  document_count: number;
}

export interface Meta {
  company_name: string;
  roles: Role[];
  purposes: string[];
  denial_reasons: string[];
  document_types: string[];
  employee_statuses: string[];
  subject_types: SubjectType[];
}

export interface Page<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}
