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

export interface ImportSummary {
  id: number;
  source_type: string;
  source_file_name: string;
  started_at: string;
  status: string;
  total_rows: number;
  error_count: number;
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

export interface ApiError {
  detail: string;
  error?: string;
}
