import type {
  ActorSummary,
  ApiError,
  DoctorResult,
  DownloadDetail,
  DownloadItemDetail,
  DownloadPage,
  DownloadPlan,
  ImportDetail,
  ImportErrorPage,
  ImportPage,
  BackupSummary,
  IntegrityResult,
  Job,
  JobCreateResponse,
  MaintenanceActionResult,
  MaintenanceSummary,
  MegaAccountStatus,
  OrphanReport,
  PlatformSummary,
  RecordDetail,
  RecordPage,
  RecordSummary,
  StatsResult,
} from './types';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = (await response.json()) as ApiError;
      message = payload.detail || payload.error || message;
    } catch {
      // Keep the HTTP fallback when the server did not return JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

const params = (values: Record<string, string | number | boolean | null | undefined>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : '';
};

export const api = {
  stats: () => request<StatsResult>('/api/stats'),
  doctor: () => request<DoctorResult>('/api/doctor'),
  maintenanceSummary: () => request<MaintenanceSummary>('/api/maintenance/summary'),
  maintenanceBackup: () =>
    request<BackupSummary>('/api/maintenance/backup', {
      method: 'POST',
    }),
  maintenanceIntegrity: () =>
    request<IntegrityResult>('/api/maintenance/integrity-check', {
      method: 'POST',
    }),
  maintenanceOrphans: () => request<OrphanReport>('/api/maintenance/orphans'),
  maintenanceAnalyze: () =>
    request<MaintenanceActionResult>('/api/maintenance/analyze', {
      method: 'POST',
    }),
  megaStatus: () => request<MegaAccountStatus>('/api/mega/status'),
  megaLogin: (body: { email: string; password: string; auth_code?: string | null }) =>
    request<MegaAccountStatus>('/api/mega/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  megaLogout: () =>
    request<MegaAccountStatus>('/api/mega/logout', {
      method: 'POST',
    }),
  actors: (query: string, limit: number) =>
    request<ActorSummary[]>(`/api/actors${params({ query, limit })}`),
  actor: (actorId: number) => request<ActorSummary>(`/api/actors/${actorId}`),
  actorRecords: (actorId: number, limit: number) =>
    request<RecordSummary[]>(`/api/actors/${actorId}/records${params({ limit })}`),
  platforms: (query: string, limit: number) =>
    request<PlatformSummary[]>(`/api/platforms${params({ query, limit })}`),
  platform: (sourceId: number) => request<PlatformSummary>(`/api/platforms/${sourceId}`),
  platformRecords: (sourceId: number, limit: number) =>
    request<RecordSummary[]>(`/api/platforms/${sourceId}/records${params({ limit })}`),
  records: (query: {
    record_id?: number;
    title?: string;
    actor?: string;
    source?: string;
    date_from?: string;
    date_to?: string;
    downloaded?: string;
    file_type?: string;
    only_undownloaded?: boolean;
    page: number;
    page_size: number;
  }) => request<RecordPage>(`/api/records${params(query)}`),
  searchTitle: (query: string, limit: number) =>
    request<RecordSummary[]>(`/api/records/search/title${params({ query, limit })}`),
  searchSource: (query: string, limit: number) =>
    request<RecordSummary[]>(`/api/records/search/source${params({ query, limit })}`),
  searchDate: (from: string, to: string, limit: number) =>
    request<RecordSummary[]>(`/api/records/search/date${params({ from, to, limit })}`),
  undownloaded: (actor: string, source: string, limit: number) =>
    request<RecordSummary[]>(`/api/records/undownloaded${params({ actor, source, limit })}`),
  record: (idOrKey: string) => request<RecordDetail>(`/api/records/${encodeURIComponent(idOrKey)}`),
  downloadPlan: (
    idOrKey: string,
    body: { include_par2: boolean; types: string | null; output?: string | null; only_undownloaded: boolean },
  ) =>
    request<DownloadPlan>(`/api/records/${encodeURIComponent(idOrKey)}/download-plan`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  createDownload: (body: {
    record_id_or_key: string;
    include_par2: boolean;
    types: string | null;
    output?: string | null;
    only_undownloaded: boolean;
  }) =>
    request<JobCreateResponse>('/api/downloads', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  downloads: (query: { status?: string; record_id?: number; page: number; page_size: number }) =>
    request<DownloadPage>(`/api/downloads${params(query)}`),
  download: (downloadId: number) => request<DownloadDetail>(`/api/downloads/${downloadId}`),
  downloadItems: (downloadId: number) =>
    request<DownloadItemDetail[]>(`/api/downloads/${downloadId}/items`),
  resumeDownload: (downloadId: number) =>
    request<JobCreateResponse>(`/api/downloads/${downloadId}/resume`, {
      method: 'POST',
    }),
  createImport: async (file: File) => {
    const body = new FormData();
    body.append('file', file);
    const response = await fetch('/api/imports', {
      method: 'POST',
      body,
    });
    if (!response.ok) {
      let message = `Request failed with ${response.status}`;
      try {
        const payload = (await response.json()) as ApiError;
        message = payload.detail || payload.error || message;
      } catch {
        // Keep the HTTP fallback when the server did not return JSON.
      }
      throw new Error(message);
    }
    return (await response.json()) as JobCreateResponse;
  },
  imports: (query: { status?: string; source_type?: string; page: number; page_size: number }) =>
    request<ImportPage>(`/api/imports${params(query)}`),
  importDetail: (importId: number) => request<ImportDetail>(`/api/imports/${importId}`),
  importErrors: (importId: number, page: number, pageSize: number) =>
    request<ImportErrorPage>(`/api/imports/${importId}/errors${params({ page, page_size: pageSize })}`),
  jobs: (query: { kind?: 'import' | 'download'; active?: boolean }) =>
    request<Job[]>(`/api/jobs${params(query)}`),
  job: (jobId: string) => request<Job>(`/api/jobs/${encodeURIComponent(jobId)}`),
};
