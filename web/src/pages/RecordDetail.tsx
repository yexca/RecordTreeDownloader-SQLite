import {
  Button,
  Checkbox,
  Divider,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconDownload, IconRefresh } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DownloadPlan, RecordDetail as RecordDetailType } from '../api/types';
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

  useEffect(() => {
    setLoading(true);
    api
      .record(idOrKey)
      .then(setRecord)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [idOrKey]);

  const buildPlan = async () => {
    try {
      setPlan(
        await api.downloadPlan(idOrKey, {
          include_par2: includePar2,
          only_undownloaded: onlyUndownloaded,
          types: types.trim() || null,
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
          <Button leftSection={<IconDownload size={16} />} disabled variant="light">
            Start download
          </Button>
        </Group>
        {plan && (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
            <Field label="Output" value={plan.output_dir} />
            <Field label="Selected links" value={plan.selected_links.length} />
            <Field label="Selected bytes" value={formatBytes(plan.selected_bytes)} />
            <Field label="Required bytes" value={formatBytes(plan.required_bytes)} />
          </SimpleGrid>
        )}
      </Stack>

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
