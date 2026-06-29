import type {
  ActorSummary,
  ApiError,
  DoctorResult,
  DownloadPlan,
  Job,
  JobCreateResponse,
  RecordDetail,
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
  actors: (query: string, limit: number) =>
    request<ActorSummary[]>(`/api/actors${params({ query, limit })}`),
  actor: (actorId: number) => request<ActorSummary>(`/api/actors/${actorId}`),
  actorRecords: (actorId: number, limit: number) =>
    request<RecordSummary[]>(`/api/actors/${actorId}/records${params({ limit })}`),
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
  job: (jobId: string) => request<Job>(`/api/jobs/${encodeURIComponent(jobId)}`),
};
