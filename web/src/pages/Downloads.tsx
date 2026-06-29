import {
  Alert,
  Button,
  Group,
  Pagination,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertCircle, IconExternalLink, IconRefresh } from '@tabler/icons-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { DownloadItemDetail, DownloadPage, Job } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { PlainStatusBadge } from '../components/StatusBadge';
import { formatBytes, formatText, previewUrl } from '../components/format';

function outputText(job: Job) {
  return job.events
    .filter((event) => event.type === 'output')
    .map((event) => String(event.data.chunk ?? ''))
    .join('');
}

function jobTarget(job: Job) {
  if (job.target?.record_id_or_key) return `Record ${String(job.target.record_id_or_key)}`;
  if (job.target?.actor_id) return `Actor ${String(job.target.actor_id)}`;
  return 'Download job';
}

export default function Downloads() {
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [history, setHistory] = useState<DownloadPage | null>(null);
  const [items, setItems] = useState<DownloadItemDetail[]>([]);
  const [selectedDownloadId, setSelectedDownloadId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const selectedDownload = useMemo(
    () => history?.items.find((item) => item.id === selectedDownloadId) ?? null,
    [history, selectedDownloadId],
  );

  const loadActiveJobs = async () => {
    try {
      setActiveJobs(await api.jobs({ kind: 'download', active: true }));
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Active jobs unavailable',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const loadHistory = async (nextPage = page) => {
    try {
      setError(null);
      setHistory(await api.downloads({ page: nextPage, page_size: 15 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download history failed to load');
    }
  };

  useEffect(() => {
    loadHistory(page);
  }, [page]);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const jobs = await api.jobs({ kind: 'download', active: true });
        if (!cancelled) setActiveJobs(jobs);
      } catch {
        // The manual refresh button reports errors; polling stays quiet.
      }
      if (!cancelled) window.setTimeout(poll, 1500);
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, []);

  const openDownload = async (downloadId: number) => {
    if (selectedDownloadId === downloadId) {
      setSelectedDownloadId(null);
      setItems([]);
      return;
    }
    setSelectedDownloadId(downloadId);
    try {
      setItems(await api.downloadItems(downloadId));
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Download items unavailable',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const refreshAll = () => {
    loadActiveJobs();
    loadHistory();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Downloads</Title>
          <Text size="sm" c="dimmed">
            Active download jobs and recorded MEGAcmd history
          </Text>
        </div>
        <Button variant="light" leftSection={<IconRefresh size={16} />} onClick={refreshAll}>
          Refresh
        </Button>
      </Group>

      <Stack p="md" className="section" gap="md">
        <Group justify="space-between">
          <Title order={3} size="h4">
            Active Jobs
          </Title>
          <Text size="sm" c="dimmed">
            {activeJobs.length} running or queued
          </Text>
        </Group>
        {activeJobs.length === 0 ? (
          <EmptyState message="No active download jobs." />
        ) : (
          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            {activeJobs.map((job) => (
              <Stack key={job.id} p="sm" className="section" gap="xs">
                <Group justify="space-between">
                  <Text fw={700}>{jobTarget(job)}</Text>
                  <PlainStatusBadge value={job.status} />
                </Group>
                <Text size="xs" c="dimmed">
                  Job {job.id}
                </Text>
                <SimpleGrid cols={2}>
                  <Text size="sm">Output: {formatText(String(job.options.output ?? 'default'))}</Text>
                  <Text size="sm">Types: {formatText(String(job.options.types ?? 'all'))}</Text>
                </SimpleGrid>
                <Textarea
                  autosize
                  minRows={3}
                  maxRows={8}
                  readOnly
                  className="log-output"
                  value={outputText(job) || 'Waiting for MEGAcmd output...'}
                />
              </Stack>
            ))}
          </SimpleGrid>
        )}
      </Stack>

      <Stack p="md" className="section" gap="md">
        <Group justify="space-between">
          <Title order={3} size="h4">
            Download History
          </Title>
          {history && (
            <Text size="sm" c="dimmed">
              {history.total} downloads
            </Text>
          )}
        </Group>
        {error && (
          <Alert color="red" icon={<IconAlertCircle size={18} />}>
            {error}
          </Alert>
        )}
        {!history ? (
          <Text size="sm" c="dimmed">
            Loading history...
          </Text>
        ) : history.items.length === 0 ? (
          <EmptyState message="No downloads recorded yet." />
        ) : (
          <>
            <div className="table-scroll">
              <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Record</Table.Th>
                    <Table.Th>Actor</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Files</Table.Th>
                    <Table.Th>Size</Table.Th>
                    <Table.Th>Output</Table.Th>
                    <Table.Th>Requested</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {history.items.map((item) => (
                    <Table.Tr
                      key={item.id}
                      className="click-row"
                      data-selected={selectedDownloadId === item.id}
                      onClick={() => openDownload(item.id)}
                    >
                      <Table.Td>{item.id}</Table.Td>
                      <Table.Td className="truncate-cell" title={item.record_title}>
                        #{item.record_group_id} {item.record_title}
                      </Table.Td>
                      <Table.Td className="truncate-cell">{item.actor}</Table.Td>
                      <Table.Td>
                        <PlainStatusBadge value={item.status} />
                      </Table.Td>
                      <Table.Td>
                        {item.completed_count}/{item.item_count}
                      </Table.Td>
                      <Table.Td className="nowrap">{formatBytes(item.selected_bytes)}</Table.Td>
                      <Table.Td className="truncate-cell" title={item.output_dir}>
                        {item.output_dir || '-'}
                      </Table.Td>
                      <Table.Td className="nowrap">{item.requested_at}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                Page {history.page} of {Math.max(1, history.total_pages)}
              </Text>
              <Pagination value={page} onChange={setPage} total={Math.max(1, history.total_pages)} />
            </Group>
          </>
        )}
      </Stack>

      {selectedDownload && (
        <Stack p="md" className="section" gap="md">
          <Group justify="space-between" align="end">
            <div>
              <Title order={3} size="h4">
                Download #{selectedDownload.id}
              </Title>
              <Text size="sm" c="dimmed">
                {selectedDownload.message || selectedDownload.output_dir || 'No message recorded.'}
              </Text>
            </div>
            <Button
              component="a"
              href={`#/records/${selectedDownload.record_group_id}`}
              variant="light"
              leftSection={<IconExternalLink size={16} />}
            >
              Open record
            </Button>
          </Group>
          <SimpleGrid cols={{ base: 2, md: 4 }}>
            <Text size="sm">Source: {selectedDownload.source}</Text>
            <Text size="sm">Exit code: {formatText(String(selectedDownload.mega_exit_code ?? ''))}</Text>
            <Text size="sm">Free before: {formatBytes(selectedDownload.free_bytes_before)}</Text>
            <Text size="sm">Failures: {selectedDownload.failed_count}</Text>
          </SimpleGrid>
          {items.length === 0 ? (
            <EmptyState message="No download items recorded for this entry." />
          ) : (
            <div className="table-scroll">
              <Table striped withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>Size</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Exit</Table.Th>
                    <Table.Th>URL</Table.Th>
                    <Table.Th>Message</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {items.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td>{item.link_order}</Table.Td>
                      <Table.Td>{formatText(item.file_type)}</Table.Td>
                      <Table.Td className="nowrap">{item.formatted_size || formatBytes(item.size_bytes)}</Table.Td>
                      <Table.Td>
                        <PlainStatusBadge value={item.status} />
                      </Table.Td>
                      <Table.Td>{formatText(String(item.mega_exit_code ?? ''))}</Table.Td>
                      <Table.Td className="url-cell" title={item.mega_url}>
                        {previewUrl(item.mega_url)}
                      </Table.Td>
                      <Table.Td className="url-cell">{formatText(item.message)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )}
        </Stack>
      )}
    </Stack>
  );
}
