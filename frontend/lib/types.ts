// Organizations
export interface Organization {
  id: string;
  name: string;
  email_domain: string;
  created_at: string;
  updated_at: string;
}

// Users
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface UserProfile {
  id: string;
  user: User;
  organization: string;
  organization_name: string;
  role: 'ADMIN' | 'ANALYST' | 'VIEWER';
  created_at: string;
  updated_at: string;
}

// Auth Token Response
export interface AuthTokenResponse {
  token: string;
}

// Data Sources
export interface DataSource {
  id: string;
  organization: string;
  source_type: 'SAP' | 'UTILITY' | 'TRAVEL';
  filename: string;
  ingested_at: string;
  ingested_by: number;
  ingested_by_name: string;
  record_count: number;
  notes: string;
}

// Emissions
export type Scope = 'SCOPE_1' | 'SCOPE_2' | 'SCOPE_3';
export type Category =
  | 'FUEL'
  | 'ELECTRICITY'
  | 'FLIGHTS'
  | 'HOTELS'
  | 'GROUND_TRANSPORT'
  | 'OTHER';
export type Status = 'NEW' | 'REVIEWED' | 'APPROVED' | 'REJECTED';

export interface RawEmission {
  id: string;
  organization: string;
  data_source: string | null;
  data_source_filename: string | null;
  source_reference_id: string;
  activity_date: string;
  activity_type: string;
  activity_value: string | number;
  activity_unit: string;
  scope: Scope;
  category: Category;
  emission_factor: string | number;
  calculated_emissions_kg_co2e: string | number;
  status: Status;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  rejection_reason: string;
  analyst_notes: string;
  validation_issues: string[];
  created_at: string;
  updated_at: string;
  audit_logs?: AuditLog[];
}

// Audit Log
export interface AuditLog {
  id: string;
  emission: string;
  action: 'CREATED' | 'UPDATED' | 'APPROVED' | 'REJECTED' | 'NOTES_ADDED';
  changed_by: number | null;
  changed_by_name: string | null;
  changes: Record<string, any>;
  timestamp: string;
  notes: string;
}

// Ingestion Response
export interface IngestionResponse {
  status: 'success' | 'partial_success' | 'error';
  data_source_id: string;
  ingested_count: number;
  errors: string[];
  warnings: string[];
  created_records: RawEmission[];
}

// Analytics
export interface AnalyticsSummary {
  total_emissions_kg_co2e: string;
  scope_1: string;
  scope_2: string;
  scope_3: string;
  by_category: Record<string, string>;
  by_status: Record<Status, number>;
  records_with_issues: number;
}

// API Responses
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface APIError {
  error?: string;
  detail?: string;
  [key: string]: any;
}
