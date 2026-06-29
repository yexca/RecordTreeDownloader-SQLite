import {
  Button,
  Checkbox,
  Divider,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconCheck, IconDownload, IconRefresh } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DownloadPlan, Job, RecordDetail as RecordDetailType } from '../api/types';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { DownloadedBadge, PlainStatusBadge } from '../components/StatusBadge';
import { formatBytes, formatText, previewUrl } from '../components/format';

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="sm">{formatText(value == null ? null : String(value))}</Text>
    </Stack>
  );
}

export default function RecordDetail({
  idOrKey,
  onBack,
}: {
  idOrKey: string;
  onBack: () => void;
}) {
  const [record, setRecord] = useState<RecordDetailType | null>(null);
  const [plan, setPlan] = useState<DownloadPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [includePar2, setIncludePar2] = useState(false);
  const [onlyUndownloaded, setOnlyUndownloaded] = useState(true);
  const [types, setTypes] = useState('');
  const [output, setOutput] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [starting, setStarting] = useState(false);
  const [confirmOpened, { open: openConfirm, close: closeConfirm }] = useDisclosure(false);

  useEffect(() => {
    setLoading(true);
    api
      .record(idOrKey)
      .then(setRecord)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [idOrKey]);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events?after=0`);
    const handleEvent = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data);
        if (!cancelled) {
          setJob((current) => {
            const base =
              current ??
              ({
                id: jobId,
                kind: 'download',
                status: 'running',
                created_at: '',
                started_at: null,
                finished_at: null,
                progress: null,
                target: null,
                options: {},
                events: [],
                result: null,
                error: null,
              } as Job);
            const events = base.events.some((item) => item.index === payload.index)
              ? base.events
              : [...base.events, payload];
            return {
              ...base,
              events,
              status: payload.type === 'completed' ? 'completed' : payload.type === 'failed' ? 'failed' : base.status,
              result: payload.type === 'completed' || payload.type === 'failed' ? payload.data.result : base.result,
              error: payload.type === 'failed' ? String(payload.data.error ?? 'Download failed') : base.error,
            };
          });
        }
      } catch {
        // Polling below remains as a fallback.
      }
    };
    source.onmessage = handleEvent;
    source.addEventListener('running', handleEvent);
    source.addEventListener('output', handleEvent);
    source.addEventListener('completed', handleEvent);
    source.addEventListener('failed', handleEvent);
    source.onerror = () => {
      source.close();
    };
    const poll = async () => {
      try {
        const next = await api.job(jobId);
        if (!cancelled) setJob(next);
        if (!cancelled && next.status !== 'completed' && next.status !== 'failed') {
          window.setTimeout(poll, 1000);
        }
      } catch (err) {
        if (!cancelled) {
          notifications.show({
            color: 'red',
            title: 'Job refresh failed',
            message: err instanceof Error ? err.message : 'Unknown error',
          });
        }
      }
    };
    poll();
    return () => {
      cancelled = true;
      source.close();
    };
  }, [jobId]);

  const buildPlan = async () => {
    try {
      setPlan(
        await api.downloadPlan(idOrKey, {
          include_par2: includePar2,
          only_undownloaded: onlyUndownloaded,
          types: types.trim() || null,
          output: output.trim() || null,
        }),
      );
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Plan unavailable',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const startDownload = async () => {
    setStarting(true);
    try {
      const created = await api.createDownload({
        record_id_or_key: idOrKey,
        include_par2: includePar2,
        only_undownloaded: onlyUndownloaded,
        types: types.trim() || null,
        output: output.trim() || null,
      });
      setJobId(created.job_id);
      setJob(null);
      closeConfirm();
      notifications.show({
        color: 'teal',
        title: 'Download started',
        message: `Job ${created.job_id}`,
      });
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Download failed to start',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setStarting(false);
    }
  };

  const outputText =
    job?.events
      .filter((event) => event.type === 'output')
      .map((event) => String(event.data.chunk ?? ''))
      .join('') ?? '';

  if (loading) return <LoadingBlock />;
  if (error) return <ErrorBlock message={error} />;
  if (!record) return <ErrorBlock message="Record not found." />;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="start">
        <Group align="start" wrap="nowrap">
          <Button variant="subtle" leftSection={<IconArrowLeft size={16} />} onClick={onBack}>
            Back
          </Button>
          <div>
            <Group gap="xs">
              <Title order={2}>{record.title}</Title>
              <DownloadedBadge value={record.downloaded} />
            </Group>
            <Text size="sm" c="dimmed">
              Record #{record.id}
            </Text>
          </div>
        </Group>
      </Group>

      <Stack p="md" className="section">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          <Field label="Actor" value={record.actor} />
          <Field label="Source" value={record.source} />
          <Field label="Delivery date" value={record.delivery_date} />
          <Field label="Entry date" value={record.entry_date} />
          <Field label="Upload title" value={record.upload_title} />
          <Field label="Size" value={record.size_raw || formatBytes(record.size_bytes)} />
          <Field label="Active links" value={`${record.completed_links}/${record.active_links}`} />
          <Field label="Inactive links" value={record.inactive_link_count} />
        </SimpleGrid>
        <Divider />
        <Field label="Source key" value={record.source_key} />
        <Field label="Note" value={record.note} />
      </Stack>

      <Stack p="md" className="section">
        <Group justify="space-between" align="end">
          <Title order={3} size="h4">
            Download Plan
          </Title>
          <Button leftSection={<IconRefresh size={16} />} onClick={buildPlan}>
            Build plan
          </Button>
        </Group>
        <Group align="end">
          <Checkbox
            label="Include .par2"
            checked={includePar2}
            onChange={(event) => setIncludePar2(event.currentTarget.checked)}
          />
          <Checkbox
            label="Only undownloaded"
            checked={onlyUndownloaded}
            onChange={(event) => setOnlyUndownloaded(event.currentTarget.checked)}
          />
          <TextInput
            label="Types"
            placeholder="mp4,m4a"
            value={types}
            onChange={(event) => setTypes(event.currentTarget.value)}
          />
          <TextInput
            label="Output"
            placeholder="Default record folder"
            value={output}
            onChange={(event) => setOutput(event.currentTarget.value)}
          />
          <Button leftSection={<IconDownload size={16} />} disabled={!plan} variant="light" onClick={openConfirm}>
            Start download
          </Button>
        </Group>
        {plan && (
          <>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
              <Field label="Output" value={plan.output_dir} />
              <Field label="Selected files" value={plan.selected_links.length} />
              <Field label="Types" value={plan.type_filter?.join(', ') || 'All'} />
              <Field label=".par2 included" value={plan.include_par2 ? 'Yes' : 'No'} />
              <Field label="Selected size" value={formatBytes(plan.selected_bytes)} />
              <Field label="Safety margin" value={formatBytes(plan.margin_bytes)} />
              <Field label="Required bytes" value={formatBytes(plan.required_bytes)} />
              <Field label="Free bytes" value={formatBytes(plan.free_bytes_before)} />
            </SimpleGrid>
            <div className="table-scroll">
              <Table striped withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th className="nowrap">#</Table.Th>
                    <Table.Th className="nowrap">Type</Table.Th>
                    <Table.Th className="nowrap">Size</Table.Th>
                    <Table.Th>URL</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {plan.selected_links.map((link) => (
                    <Table.Tr key={link.id}>
                      <Table.Td className="nowrap">{link.link_order}</Table.Td>
                      <Table.Td className="nowrap">{formatText(link.file_type)}</Table.Td>
                      <Table.Td className="nowrap">{link.formatted_size || formatBytes(link.size_bytes)}</Table.Td>
                      <Table.Td className="url-cell" title={link.mega_url}>
                        {previewUrl(link.mega_url)}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          </>
        )}
        {jobId && (
          <Stack gap="xs">
            <Group gap="xs">
              <Text size="sm" fw={700}>
                Job {jobId}
              </Text>
              {job && <PlainStatusBadge value={job.status} />}
            </Group>
            {job?.error && (
              <Text size="sm" c="red">
                {job.error}
              </Text>
            )}
            <Textarea
              autosize
              minRows={4}
              maxRows={12}
              readOnly
              className="log-output"
              value={outputText || 'Waiting for MEGAcmd output...'}
            />
          </Stack>
        )}
      </Stack>

      <Modal opened={confirmOpened} onClose={closeConfirm} title="Confirm download" centered>
        <Stack gap="sm">
          <Text size="sm">
            Start downloading {plan?.selected_links.length ?? 0} files to {plan?.output_dir ?? ''}?
          </Text>
          <SimpleGrid cols={2}>
            <Field label="Selected size" value={formatBytes(plan?.selected_bytes ?? null)} />
            <Field label="Required bytes" value={formatBytes(plan?.required_bytes ?? null)} />
            <Field label="Free bytes" value={formatBytes(plan?.free_bytes_before ?? null)} />
            <Field label=".par2 included" value={plan?.include_par2 ? 'Yes' : 'No'} />
          </SimpleGrid>
          <Group justify="end">
            <Button variant="subtle" onClick={closeConfirm}>
              Cancel
            </Button>
            <Button leftSection={<IconCheck size={16} />} loading={starting} onClick={startDownload}>
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Stack p="md" className="section">
        <Title order={3} size="h4">
          Active Links
        </Title>
        <div className="table-scroll">
          <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th className="nowrap">#</Table.Th>
                <Table.Th className="nowrap">Type</Table.Th>
                <Table.Th className="nowrap">Size</Table.Th>
                <Table.Th className="nowrap">Status</Table.Th>
                <Table.Th>URL</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {record.links.map((link) => (
                <Table.Tr key={link.id}>
                  <Table.Td className="nowrap">{link.link_order}</Table.Td>
                  <Table.Td className="nowrap">{formatText(link.file_type)}</Table.Td>
                  <Table.Td className="nowrap">{link.formatted_size || formatBytes(link.size_bytes)}</Table.Td>
                  <Table.Td className="nowrap">
                    <PlainStatusBadge value={link.status} />
                  </Table.Td>
                  <Table.Td className="url-cell" title={link.mega_url}>
                    {previewUrl(link.mega_url)}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </Stack>
    </Stack>
  );
}
