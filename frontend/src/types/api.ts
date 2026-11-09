export type UserRole = "client" | "lawyer" | "admin";

export interface User {
  id: number;
  email: string;
  phone: string | null;
  full_name: string | null;
  city: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface Lawyer {
  id: number;
  user_id: number;
  full_name: string;
  specialization: string | null;
  city: string | null;
  years_of_experience: number;
  consultation_fee: string | number | null;
  languages: string[];
  office_address: string | null;
  verified: boolean;
}

export interface ApiError {
  detail?: string | { msg?: string }[];
}
