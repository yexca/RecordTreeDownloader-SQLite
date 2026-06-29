export type DownloadedStatus = 'all' | 'partial' | 'none' | 'unknown';
export type CheckStatus = 'pass' | 'warn' | 'fail';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface StatsResult {
  total_record_groups: number;
  active_link_count: number;
  inactive_link_count: number;
  actor_count: number;
  source_count: number;
  downloaded_all: number;
  downloaded_partial: number;
  downloaded_none: number;
  downloaded_unknown: number;
  recent_imports: ImportSummary[];
  recent_downloads: DownloadSummary[];
}

export interface BackupSummary {
  path: string;
  size_bytes: number;
  created_at: string;
}

export interface MaintenanceSummary {
  doctor: DoctorResult;
  doctor_ok: boolean;
  stats: StatsResult;
  database_path: string;
  database_size_bytes: number | null;
  backup_dir: string;
  latest_backup: BackupSummary | null;
}

export interface MaintenanceActionResult {
  ok: boolean;
  message: string;
  started_at: string;
  finished_at: string;
}

export interface IntegrityResult {
  ok: boolean;
  quick_check: string;
  foreign_key_violations: number;
  checks: DoctorCheck[];
}

export interface OrphanReport {
  ok: boolean;
  actors_without_records: number;
  sources_without_records: number;
  record_actor_orphans: number;
  record_source_orphans: number;
  links_without_record: number;
  downloads_without_record: number;
  download_items_without_download: number;
  download_items_without_link: number;
}

export interface ImportSummary {
  id: number;
  source_type: string;
  source_file_name: string;
  started_at: string;
  status: string;
  total_rows: number;
  error_count: number;
}

export interface ImportDetail {
  id: number;
  source_type: string;
  source_path: string;
  source_file_name: string;
  source_file_size: number | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  total_rows: number;
  inserted_groups: number;
  updated_groups: number;
  skipped_groups: number;
  link_sets_changed: number;
  inserted_links: number;
  skipped_links: number;
  error_count: number;
  notes: string | null;
}

export interface ImportPage {
  items: ImportDetail[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ImportErrorRow {
  id: number;
  import_id: number;
  row_number: number | null;
  source_key: string | null;
  error_type: string;
  message: string;
  raw_value: string | null;
  created_at: string;
}

export interface ImportErrorPage {
  items: ImportErrorRow[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ImportStats {
  total_rows: number;
  inserted_groups: number;
  updated_groups: number;
  skipped_groups: number;
  link_sets_changed: number;
  inserted_links: number;
  skipped_links: number;
  error_count: number;
}

export interface ImportResult {
  import_id: number;
  source_type: string;
  source_path: string;
  status: string;
  stats: ImportStats;
  error_csv_path: string | null;
  extra_columns: string[];
  notes: string | null;
}

export interface JobProgress {
  phase: string;
  source_type: string;
  source_path: string;
  completed_rows: number;
  total_rows: number | null;
}

export interface JobEvent {
  index: number;
  type: string;
  created_at: string;
  data: Record<string, unknown>;
}

export interface DownloadExecutionResult {
  download_id: number;
  record_group_id: number;
  status: string;
  completed: number;
  failed: number;
  output_dir: string;
  message: string | null;
}

export interface Job {
  id: string;
  kind: 'import' | 'download';
  status: JobStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  progress: JobProgress | null;
  target: Record<string, unknown> | null;
  options: Record<string, unknown>;
  events: JobEvent[];
  result: ImportResult | DownloadExecutionResult | Record<string, unknown> | null;
  error: string | null;
}

export type ImportJob = Job & {
  kind: 'import';
  result: ImportResult | null;
};

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
}

export interface DownloadSummary {
  id: number;
  record_group_id: number;
  requested_at: string;
  status: string;
  selected_bytes: number;
  message: string | null;
}

export interface DownloadDetail {
  id: number;
  record_group_id: number;
  record_title: string;
  actor: string;
  source: string;
  requested_at: string;
  output_dir: string;
  selected_bytes: number;
  free_bytes_before: number | null;
  status: string;
  mega_exit_code: number | null;
  message: string | null;
  request_json: string | null;
  item_count: number;
  completed_count: number;
  failed_count: number;
}

export interface DownloadPage {
  items: DownloadDetail[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface DownloadItemDetail {
  id: number;
  download_id: number;
  link_id: number;
  link_order: number;
  mega_url: string;
  file_type: string | null;
  size_bytes: number;
  formatted_size: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  mega_exit_code: number | null;
  message: string | null;
}

export interface ActorSummary {
  id: number;
  name: string;
  record_count: number;
  undownloaded_count: number;
}

export interface PlatformSummary {
  id: number;
  name: string;
  record_count: number;
  undownloaded_count: number;
}

export interface RecordSummary {
  id: number;
  source_key: string;
  delivery_date: string | null;
  entry_date: string | null;
  actor: string | null;
  title: string;
  source: string | null;
  size_bytes: number | null;
  active_links: number;
  completed_links: number;
  downloaded: DownloadedStatus;
}

export interface RecordPage {
  items: RecordSummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface LinkSummary {
  id: number;
  link_order: number;
  mega_url: string;
  file_type: string | null;
  size_bytes: number;
  formatted_size: string | null;
  status: string;
}

export interface RecordDetail {
  id: number;
  source_key: string;
  actor: string;
  delivery_date: string | null;
  entry_date: string | null;
  title: string;
  source: string;
  upload_title: string;
  note: string | null;
  size_bytes: number | null;
  size_raw: string | null;
  active_links: number;
  completed_links: number;
  downloaded: DownloadedStatus;
  links: LinkSummary[];
  inactive_link_count: number;
}

export interface DownloadPlan {
  record_group_id: number;
  output_dir: string;
  actor: string;
  title: string;
  selected_links: LinkSummary[];
  selected_bytes: number;
  margin_bytes: number;
  required_bytes: number;
  free_bytes_before: number | null;
  include_par2: boolean;
  type_filter: string[] | null;
}

export interface DoctorResult {
  checks: DoctorCheck[];
  ok: boolean;
}

export interface DoctorCheck {
  name: string;
  status: CheckStatus;
  message: string;
}

export interface MegaLoginStatus {
  logged_in: boolean;
  exit_code: number;
  message: string;
}

export interface MegaCommandStatus {
  configured: string;
  resolved: string | null;
  available: boolean;
  message: string;
}

export interface MegaAccountStatus {
  login: MegaLoginStatus;
  mega_get: MegaCommandStatus;
  mega_whoami: MegaCommandStatus;
  mega_login: MegaCommandStatus;
  mega_logout: MegaCommandStatus;
  home_dir: string;
  persistence_dir: string;
}

export interface ApiError {
  detail: string;
  error?: string;
}
