import {
  Alert,
  Button,
  Group,
  List,
  Progress,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertCircle, IconFileImport, IconUpload } from '@tabler/icons-react';
import { DragEvent, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import type { ImportJob, ImportResult, Job, JobProgress } from '../api/types';
import { PlainStatusBadge } from '../components/StatusBadge';

const ACCEPTED_EXTENSIONS = ['.xlsx', '.xlsm', '.json', '.db', '.sqlite', '.sqlite3'];

function extensionOf(file: File) {
  return file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
}

function progressPercent(progress: JobProgress | null) {
  if (!progress || !progress.total_rows || progress.total_rows <= 0) return 0;
  return Math.min(100, Math.round((progress.completed_rows / progress.total_rows) * 100));
}

function Stat({ label, value }: { label: string; value: number | string | null }) {
  return (
    <Stack gap={2} p="sm" className="section">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={700}>{value ?? '-'}</Text>
    </Stack>
  );
}

function ResultSummary({ result }: { result: ImportResult }) {
  return (
    <Stack gap="sm">
      <Group justify="space-between">
        <Title order={3} size="h4">
          Import Summary
        </Title>
        <PlainStatusBadge value={result.status} />
      </Group>
      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Stat label="Import ID" value={result.import_id} />
        <Stat label="Source type" value={result.source_type} />
        <Stat label="Total rows" value={result.stats.total_rows} />
        <Stat label="Errors" value={result.stats.error_count} />
        <Stat label="Inserted groups" value={result.stats.inserted_groups} />
        <Stat label="Updated groups" value={result.stats.updated_groups} />
        <Stat label="Link sets changed" value={result.stats.link_sets_changed} />
        <Stat label="Inserted links" value={result.stats.inserted_links} />
        <Stat label="Skipped links" value={result.stats.skipped_links} />
        <Stat label="Error CSV" value={result.error_csv_path} />
      </SimpleGrid>
      <Table withTableBorder fz="sm">
        <Table.Tbody>
          <Table.Tr>
            <Table.Th w={160}>Source path</Table.Th>
            <Table.Td className="url-cell">{result.source_path}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Th>Notes</Table.Th>
            <Table.Td>{result.notes || '-'}</Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>
    </Stack>
  );
}

function asImportJob(job: Job): ImportJob {
  return job as ImportJob;
}

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const canUpload = useMemo(() => file && ACCEPTED_EXTENSIONS.includes(extensionOf(file)), [file]);
  const percent = progressPercent(job?.progress ?? null);

  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') return;
    timerRef.current = window.setInterval(async () => {
      try {
        setJob(asImportJob(await api.job(job.id)));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Job polling failed');
      }
    }, 1000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [job?.id, job?.status]);

  const startImport = async () => {
    if (!file || !canUpload) return;
    setUploading(true);
    setError(null);
    try {
      const created = await api.createImport(file);
      const next = await api.job(created.job_id);
      setJob(asImportJob(next));
      notifications.show({ color: 'teal', title: 'Import queued', message: file.name });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setUploading(false);
    }
  };

  const pickFile = (selected: FileList | null) => {
    setFile(selected?.[0] ?? null);
  };

  const dropFile = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    pickFile(event.dataTransfer.files);
  };

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Import</Title>
        <Text size="sm" c="dimmed">
          Upload a source file and track the background import job
        </Text>
      </div>

      <Stack p="md" className="section" gap="md">
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          hidden
          onChange={(event) => pickFile(event.currentTarget.files)}
        />
        <UnstyledButton
          className="dropzone"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={dropFile}
          disabled={uploading}
        >
          <Group justify="center" gap="md" mih={120}>
            <IconUpload size={28} />
            <Stack gap={2}>
              <Text fw={700}>{file ? file.name : 'Select or drop an import file'}</Text>
              <Text size="sm" c="dimmed">
                .xlsx, .xlsm, .json, .db, .sqlite, .sqlite3
              </Text>
            </Stack>
          </Group>
        </UnstyledButton>

        {file && !canUpload && (
          <Alert color="red" icon={<IconAlertCircle size={18} />}>
            Unsupported file extension.
          </Alert>
        )}
        {error && (
          <Alert color="red" icon={<IconAlertCircle size={18} />}>
            {error}
          </Alert>
        )}

        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            {job ? `Job ${job.id}` : 'No import job started.'}
          </Text>
          <Button
            leftSection={<IconFileImport size={16} />}
            onClick={startImport}
            disabled={!canUpload || uploading}
            loading={uploading}
          >
            Start Import
          </Button>
        </Group>
      </Stack>

      {job && (
        <Stack p="md" className="section" gap="md">
          <Group justify="space-between">
            <Title order={3} size="h4">
              Progress
            </Title>
            <PlainStatusBadge value={job.status} />
          </Group>
          <Progress value={percent} animated={job.status === 'running'} />
          <SimpleGrid cols={{ base: 2, md: 4 }}>
            <Stat label="Phase" value={job.progress?.phase ?? job.status} />
            <Stat label="Completed rows" value={job.progress?.completed_rows ?? 0} />
            <Stat label="Total rows" value={job.progress?.total_rows ?? '-'} />
            <Stat label="Source type" value={job.progress?.source_type ?? '-'} />
          </SimpleGrid>
          {job.error && (
            <Alert color="red" icon={<IconAlertCircle size={18} />}>
              {job.error}
            </Alert>
          )}
          {job.result && <ResultSummary result={job.result} />}
          <List size="sm" spacing={4}>
            {job.events.slice(-5).map((event) => (
              <List.Item key={event.index}>
                <Text span c="dimmed">
                  {event.created_at}
                </Text>{' '}
                {event.type}
              </List.Item>
            ))}
          </List>
        </Stack>
      )}
    </Stack>
  );
}
