import type { UserRole } from "@/types/api";

export interface Appointment {
  id: string;
  client_id: number;
  lawyer_id: number;
  appointment_date: string;
  appointment_time: string;
  consultation_type: "online" | "in_person";
  notes: string | null;
  status: "pending" | "approved" | "rejected" | "completed" | "cancelled";
  created_at: string;
  updated_at: string;
}

export interface Availability {
  id: string;
  lawyer_id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export type CaseStatus =
  | "open"
  | "in_progress"
  | "waiting_client"
  | "on_hold"
  | "closed";

export interface LegalCase {
  id: string;
  client_id: number;
  lawyer_id: number;
  title: string;
  description: string;
  case_type: string;
  status: CaseStatus;
  priority: "low" | "medium" | "high" | "urgent";
  created_at: string;
  updated_at: string;
}

export interface CaseNote {
  id: string;
  case_id: string;
  author_id: number;
  note: string;
  created_at: string;
}

export interface CaseStatusEvent {
  id: string;
  case_id: string;
  changed_by_id: number;
  previous_status: CaseStatus | null;
  new_status: CaseStatus;
  created_at: string;
}

export interface CaseDocument {
  id: string;
  case_id: string;
  uploaded_by: number;
  document_type:
    | "contract"
    | "evidence"
    | "court_order"
    | "agreement"
    | "id_document"
    | "other";
  file_name: string;
  original_file_name: string;
  file_type: string;
  file_size: number;
  storage_url: string;
  description: string | null;
  uploaded_at: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface AdminUser {
  id: number;
  email: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface PendingLawyer {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  phone: string | null;
  license_number: string;
  bar_council: string;
  bar_council_number: string;
  specialization: string | null;
  city: string | null;
  years_of_experience: number;
  verification_status: string;
}

export interface AdminStats {
  total_users: number;
  total_lawyers: number;
  total_clients: number;
  total_cases: number;
  pending_appointments: number;
  approved_lawyers: number;
}
