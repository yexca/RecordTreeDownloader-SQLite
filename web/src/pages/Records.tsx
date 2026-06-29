import {
  Button,
  Checkbox,
  Group,
  NumberInput,
  Pagination,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh, IconSearch } from '@tabler/icons-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DownloadedStatus, RecordPage } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { RecordTable } from '../components/RecordTable';

const emptyPage: RecordPage = {
  items: [],
  page: 1,
  page_size: 50,
  total: 0,
  total_pages: 0,
};

export default function Records({ onOpenRecord }: { onOpenRecord: (id: number) => void }) {
  const [title, setTitle] = useState('');
  const [actor, setActor] = useState('');
  const [source, setSource] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [downloaded, setDownloaded] = useState<DownloadedStatus | ''>('');
  const [fileType, setFileType] = useState('');
  const [onlyUndownloaded, setOnlyUndownloaded] = useState(false);
  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<RecordPage>(emptyPage);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const loadRecords = async (nextPage = page) => {
    setLoading(true);
    setSearched(true);
    try {
      const payload = await api.records({
        title,
        actor,
        source,
        date_from: dateFrom,
        date_to: dateTo,
        downloaded,
        file_type: fileType,
        only_undownloaded: onlyUndownloaded,
        page: nextPage,
        page_size: pageSize,
      });
      setResult(payload);
      setPage(payload.page);
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Records query failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const runQuery = (event?: FormEvent) => {
    event?.preventDefault();
    setPage(1);
    void loadRecords(1);
  };

  const resetFilters = () => {
    setTitle('');
    setActor('');
    setSource('');
    setDateFrom('');
    setDateTo('');
    setDownloaded('');
    setFileType('');
    setOnlyUndownloaded(false);
    setPage(1);
  };

  useEffect(() => {
    void loadRecords(1);
    // Initial load only; searches after edits are explicit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const start = result.total === 0 ? 0 : (result.page - 1) * result.page_size + 1;
  const end = Math.min(result.page * result.page_size, result.total);

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Records</Title>
        <Text size="sm" c="dimmed">
          Browse and filter record groups
        </Text>
      </div>

      <form onSubmit={runQuery}>
        <Stack p="md" className="section" gap="sm">
          <Group grow align="end">
            <TextInput label="Title" value={title} onChange={(event) => setTitle(event.currentTarget.value)} />
            <TextInput label="Actor" value={actor} onChange={(event) => setActor(event.currentTarget.value)} />
            <TextInput label="Source" value={source} onChange={(event) => setSource(event.currentTarget.value)} />
          </Group>
          <Group grow align="end">
            <TextInput
              label="From"
              placeholder="YYYY-MM-DD"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.currentTarget.value)}
            />
            <TextInput
              label="To"
              placeholder="YYYY-MM-DD"
              value={dateTo}
              onChange={(event) => setDateTo(event.currentTarget.value)}
            />
            <Select
              label="Status"
              clearable
              value={downloaded}
              onChange={(value) => setDownloaded((value as DownloadedStatus | null) ?? '')}
              data={[
                { value: 'all', label: 'All downloaded' },
                { value: 'partial', label: 'Partial' },
                { value: 'none', label: 'None' },
                { value: 'unknown', label: 'Unknown' },
              ]}
            />
          </Group>
          <Group align="end">
            <TextInput
              label="File type"
              placeholder="mp4"
              value={fileType}
              onChange={(event) => setFileType(event.currentTarget.value)}
            />
            <NumberInput
              label="Page size"
              className="records-page-size"
              value={pageSize}
              min={1}
              max={500}
              step={10}
              onChange={(value) => setPageSize(Number(value) || 50)}
            />
            <Checkbox
              label="Only undownloaded"
              checked={onlyUndownloaded}
              onChange={(event) => setOnlyUndownloaded(event.currentTarget.checked)}
            />
            <Button type="submit" leftSection={<IconSearch size={16} />} loading={loading}>
              Search
            </Button>
            <Button type="button" variant="light" leftSection={<IconRefresh size={16} />} onClick={resetFilters}>
              Reset
            </Button>
          </Group>
        </Stack>
      </form>

      <Stack p="md" className="section" gap="sm">
        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            {result.total ? `${start}-${end} of ${result.total}` : searched ? '0 records' : 'Loading records'}
          </Text>
          <Pagination
            value={page}
            total={Math.max(result.total_pages, 1)}
            disabled={loading || result.total_pages <= 1}
            onChange={(nextPage) => {
              setPage(nextPage);
              void loadRecords(nextPage);
            }}
          />
        </Group>

        {result.items.length === 0 ? (
          <EmptyState message={searched ? 'No records found.' : 'Records will appear here.'} />
        ) : (
          <RecordTable records={result.items} onOpen={onOpenRecord} />
        )}
      </Stack>
    </Stack>
  );
}
