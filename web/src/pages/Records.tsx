import {
  ActionIcon,
  Group,
  NumberInput,
  Pagination,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { DateInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';
import { IconRefresh, IconSearch } from '@tabler/icons-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DownloadedStatus, RecordPage } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { RecordTable } from '../components/RecordTable';
import { useCachedState } from '../state/pageState';

type DownloadFilter = DownloadedStatus | 'pending' | '';

const emptyPage: RecordPage = {
  items: [],
  page: 1,
  page_size: 50,
  total: 0,
  total_pages: 0,
};

export default function Records({ onOpenRecord }: { onOpenRecord: (id: number) => void }) {
  const [recordId, setRecordId] = useCachedState('records.recordId', '');
  const [title, setTitle] = useCachedState('records.title', '');
  const [actor, setActor] = useCachedState('records.actor', '');
  const [source, setSource] = useCachedState('records.source', '');
  const [dateFrom, setDateFrom] = useCachedState<string | null>('records.dateFrom', null);
  const [dateTo, setDateTo] = useCachedState<string | null>('records.dateTo', null);
  const [downloadFilter, setDownloadFilter] = useCachedState<DownloadFilter>('records.downloadFilter', '');
  const [pageSize, setPageSize] = useCachedState('records.pageSize', 50);
  const [page, setPage] = useCachedState('records.page', 1);
  const [result, setResult] = useCachedState<RecordPage>('records.result', emptyPage);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useCachedState('records.searched', false);

  const loadRecords = async (nextPage = page) => {
    setLoading(true);
    setSearched(true);
    const parsedRecordId = Number(recordId);
    const hasRecordId = recordId.trim() !== '' && Number.isInteger(parsedRecordId);
    if (recordId.trim() !== '' && !hasRecordId) {
      notifications.show({
        color: 'red',
        title: 'Invalid record ID',
        message: 'Record ID must be a whole number.',
      });
      setLoading(false);
      return;
    }
    try {
      const payload = await api.records({
        record_id: hasRecordId ? parsedRecordId : undefined,
        title,
        actor,
        source,
        date_from: dateFrom ?? '',
        date_to: dateTo ?? '',
        downloaded: downloadFilter === 'pending' ? '' : downloadFilter,
        only_undownloaded: downloadFilter === 'pending',
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
    setRecordId('');
    setTitle('');
    setActor('');
    setSource('');
    setDateFrom(null);
    setDateTo(null);
    setDownloadFilter('');
    setPage(1);
  };

  useEffect(() => {
    if (!searched) void loadRecords(1);
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
        <div className="section records-toolbar">
          <TextInput
            aria-label="Record ID"
            placeholder="ID"
            value={recordId}
            inputMode="numeric"
            onChange={(event) => setRecordId(event.currentTarget.value)}
          />
          <TextInput
            aria-label="Title"
            placeholder="Title"
            value={title}
            onChange={(event) => setTitle(event.currentTarget.value)}
          />
          <TextInput
            aria-label="Actor"
            placeholder="Actor"
            value={actor}
            onChange={(event) => setActor(event.currentTarget.value)}
          />
          <TextInput
            aria-label="Source"
            placeholder="Source"
            value={source}
            onChange={(event) => setSource(event.currentTarget.value)}
          />
          <Group gap={4} wrap="nowrap" className="records-date-filter">
            <DateInput
              aria-label="From delivery date"
              placeholder="From"
              value={dateFrom}
              onChange={setDateFrom}
              valueFormat="YYYY-MM-DD"
              clearable
            />
            <Text size="sm" c="dimmed" className="records-date-separator">
              to
            </Text>
            <DateInput
              aria-label="To delivery date"
              placeholder="To"
              value={dateTo}
              onChange={setDateTo}
              valueFormat="YYYY-MM-DD"
              clearable
            />
          </Group>
          <Select
            aria-label="Download status"
            placeholder="Download"
            clearable
            value={downloadFilter}
            onChange={(value) => setDownloadFilter((value as DownloadFilter | null) ?? '')}
            data={[
              { value: 'pending', label: 'Pending links' },
              { value: 'all', label: 'Complete' },
              { value: 'partial', label: 'Partial' },
              { value: 'none', label: 'Not downloaded' },
              { value: 'unknown', label: 'No links' },
            ]}
          />
          <Tooltip label="Search records">
            <ActionIcon type="submit" size="lg" loading={loading} aria-label="Search records">
              <IconSearch size={18} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Reset filters">
            <ActionIcon type="button" size="lg" variant="light" aria-label="Reset filters" onClick={resetFilters}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
        </div>
      </form>

      <Stack p="md" className="section" gap="sm">
        <Group justify="space-between" gap="sm" wrap="nowrap" className="records-result-bar">
          <Text size="sm" c="dimmed" className="nowrap">
            {result.total ? `${start}-${end} / ${result.total}` : searched ? '0 records' : 'Loading records'}
          </Text>
          <Group gap="xs" wrap="nowrap">
            <NumberInput
              aria-label="Page size"
              className="records-page-size"
              value={pageSize}
              min={1}
              max={500}
              step={10}
              onChange={(value) => setPageSize(Number(value) || 50)}
            />
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
