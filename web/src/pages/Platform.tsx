import {
  ActionIcon,
  Badge,
  Group,
  Pagination,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconRefresh, IconSearch } from '@tabler/icons-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { PlatformSummary, RecordSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { RecordTable } from '../components/RecordTable';
import RecordDetail from './RecordDetail';

const PLATFORM_FETCH_LIMIT = 500;
const DEFAULT_PLATFORMS_PER_PAGE = 25;
const RECORD_FETCH_LIMIT = 500;
const DEFAULT_RECORDS_PER_PAGE = 25;
type SearchMode = 'name' | 'id';

export default function Platform() {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('name');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PLATFORMS_PER_PAGE);
  const [recordPage, setRecordPage] = useState(1);
  const [recordsPerPage, setRecordsPerPage] = useState(DEFAULT_RECORDS_PER_PAGE);
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformSummary | null>(null);
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [loadingPlatforms, setLoadingPlatforms] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [platformError, setPlatformError] = useState<string | null>(null);
  const [recordError, setRecordError] = useState<string | null>(null);

  const loadPlatforms = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoadingPlatforms(true);
    setPlatformError(null);
    try {
      const id = Number(query.trim());
      const nextPlatforms =
        searchMode === 'id' && Number.isInteger(id) && id > 0
          ? [await api.platform(id)]
          : await api.platforms(searchMode === 'name' ? query : '', PLATFORM_FETCH_LIMIT);
      setPlatforms(nextPlatforms);
      setPage(1);
      if (selectedPlatform && !nextPlatforms.some((platform) => platform.id === selectedPlatform.id)) {
        setSelectedPlatform(null);
        setRecords([]);
        setSelectedRecordId(null);
      }
    } catch (err) {
      setPlatformError(err instanceof Error ? err.message : 'Platform search failed');
    } finally {
      setLoadingPlatforms(false);
    }
  };

  const loadPlatformRecords = async (platform: PlatformSummary) => {
    setSelectedPlatform(platform);
    setSelectedRecordId(null);
    setRecordPage(1);
    setLoadingRecords(true);
    setRecordError(null);
    try {
      setRecords(await api.platformRecords(platform.id, RECORD_FETCH_LIMIT));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Platform records failed';
      setRecordError(message);
      notifications.show({
        color: 'red',
        title: 'Records unavailable',
        message,
      });
    } finally {
      setLoadingRecords(false);
    }
  };

  useEffect(() => {
    loadPlatforms();
    // Initial load only; search form and refresh button control later requests.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const trimmedQuery = query.trim();
  const visiblePlatforms =
    searchMode === 'id' && trimmedQuery
      ? platforms.filter((platform) => String(platform.id).includes(trimmedQuery))
      : platforms;
  const totalPages = Math.max(1, Math.ceil(visiblePlatforms.length / perPage));
  const safePage = Math.min(page, totalPages);
  const pagePlatforms = visiblePlatforms.slice((safePage - 1) * perPage, safePage * perPage);
  const rangeStart = visiblePlatforms.length === 0 ? 0 : (safePage - 1) * perPage + 1;
  const rangeEnd = Math.min(safePage * perPage, visiblePlatforms.length);
  const totalRecordPages = Math.max(1, Math.ceil(records.length / recordsPerPage));
  const safeRecordPage = Math.min(recordPage, totalRecordPages);
  const pageRecords = records.slice(
    (safeRecordPage - 1) * recordsPerPage,
    safeRecordPage * recordsPerPage,
  );
  const recordRangeStart = records.length === 0 ? 0 : (safeRecordPage - 1) * recordsPerPage + 1;
  const recordRangeEnd = Math.min(safeRecordPage * recordsPerPage, records.length);

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Platform</Title>
          <Text size="sm" c="dimmed">
            Browse platform directories and open related records.
          </Text>
        </div>
      </Group>

      <div className="actors-layout">
        <Stack className="section actor-directory" gap={0}>
          <form onSubmit={loadPlatforms}>
            <Stack gap="sm" p="md" className="actor-directory-toolbar">
              <Group justify="space-between" align="start" wrap="nowrap">
                <div>
                  <Title order={3} size="h4">
                    Directory
                  </Title>
                  <Text size="xs" c="dimmed">
                    {visiblePlatforms.length} shown, {platforms.length} loaded
                  </Text>
                </div>
                <Tooltip label="Refresh platforms">
                  <ActionIcon
                    variant="subtle"
                    size={32}
                    aria-label="Refresh platforms"
                    loading={loadingPlatforms}
                    onClick={() => loadPlatforms()}
                  >
                    <IconRefresh size={16} />
                  </ActionIcon>
                </Tooltip>
              </Group>
              <Group className="actor-search-row" gap="xs" wrap="nowrap">
                <Select
                  aria-label="Search mode"
                  value={searchMode}
                  onChange={(value) => {
                    setSearchMode((value as SearchMode | null) ?? 'name');
                    setPage(1);
                  }}
                  data={[
                    { value: 'name', label: 'Name' },
                    { value: 'id', label: 'ID' },
                  ]}
                  allowDeselect={false}
                  className="actor-search-mode"
                />
                <TextInput
                  aria-label="Search platform"
                  placeholder={searchMode === 'id' ? 'Platform ID' : 'Platform name'}
                  value={query}
                  onChange={(event) => {
                    setQuery(event.currentTarget.value);
                    if (searchMode === 'id') setPage(1);
                  }}
                  className="actor-search-input"
                />
                <Tooltip label="Search">
                  <ActionIcon
                    type="submit"
                    variant="filled"
                    size={36}
                    aria-label="Search platforms"
                    loading={loadingPlatforms}
                  >
                    <IconSearch size={16} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Stack>
          </form>

          <div className="actor-directory-body">
            {platformError ? (
              <ErrorBlock message={platformError} />
            ) : loadingPlatforms ? (
              <LoadingBlock />
            ) : platforms.length === 0 ? (
              <EmptyState message="No platforms found." />
            ) : (
              <ScrollArea.Autosize mah="calc(100vh - 330px)" type="auto">
                <Stack gap={4} p="xs">
                  {pagePlatforms.map((platform) => (
                    <button
                      key={platform.id}
                      type="button"
                      className="actor-list-item"
                      data-selected={selectedPlatform?.id === platform.id || undefined}
                      onClick={() => loadPlatformRecords(platform)}
                    >
                      <span className="actor-list-main">
                        <Text size="sm" fw={700} className="truncate-cell" title={platform.name}>
                          {platform.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          ID {platform.id} | {platform.record_count} records
                        </Text>
                      </span>
                      <Badge variant="light" color={platform.undownloaded_count > 0 ? 'yellow' : 'teal'} size="sm">
                        {platform.undownloaded_count}
                      </Badge>
                    </button>
                  ))}
                </Stack>
              </ScrollArea.Autosize>
            )}
          </div>

          {platforms.length > 0 && !platformError && (
            <Stack className="actor-directory-footer" gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap">
                <Text size="xs" c="dimmed">
                  {rangeStart}-{rangeEnd} of {visiblePlatforms.length}
                </Text>
                <Select
                  aria-label="Platforms per page"
                  value={String(perPage)}
                  onChange={(value) => {
                    setPerPage(Number(value) || DEFAULT_PLATFORMS_PER_PAGE);
                    setPage(1);
                  }}
                  data={[
                    { value: '10', label: '10 / page' },
                    { value: '25', label: '25 / page' },
                    { value: '50', label: '50 / page' },
                    { value: '100', label: '100 / page' },
                  ]}
                  allowDeselect={false}
                  size="xs"
                  className="actor-page-size"
                />
              </Group>
              <Pagination
                total={totalPages}
                value={safePage}
                onChange={setPage}
                size="xs"
                siblings={0}
                boundaries={1}
              />
            </Stack>
          )}
        </Stack>

        <Stack className="actor-workspace" gap="md">
          {!selectedPlatform ? (
            <Stack className="section actor-empty-state" align="center" justify="center" gap="xs">
              <Title order={3} size="h4">
                Select a platform
              </Title>
              <Text size="sm" c="dimmed" ta="center">
                Choose a platform from the directory to review records and download coverage.
              </Text>
            </Stack>
          ) : (
            <>
              <Group className="section actor-summary" justify="space-between" align="start" wrap="nowrap">
                <div>
                  <Title order={3} size="h4">
                    {selectedPlatform.name}
                  </Title>
                  <Group gap="xs" mt={4}>
                    <Badge variant="light">{selectedPlatform.record_count} records</Badge>
                    <Badge variant="light" color={selectedPlatform.undownloaded_count > 0 ? 'yellow' : 'teal'}>
                      {selectedPlatform.undownloaded_count} undownloaded
                    </Badge>
                  </Group>
                </div>
                <ActionIcon
                  variant="subtle"
                  aria-label="Clear platform selection"
                  onClick={() => {
                    setSelectedPlatform(null);
                    setRecords([]);
                    setSelectedRecordId(null);
                  }}
                >
                  <IconArrowLeft size={18} />
                </ActionIcon>
              </Group>

              {selectedRecordId ? (
                <RecordDetail idOrKey={String(selectedRecordId)} onBack={() => setSelectedRecordId(null)} />
              ) : (
                <Stack p="md" className="section" gap="md">
                  <Group justify="space-between" align="center">
                    <Title order={3} size="h4">
                      Records
                    </Title>
                    <Group gap="xs" wrap="nowrap">
                      <Text size="xs" c="dimmed">
                        Sorted by delivery date
                      </Text>
                      <Select
                        aria-label="Records per page"
                        value={String(recordsPerPage)}
                        onChange={(value) => {
                          setRecordsPerPage(Number(value) || DEFAULT_RECORDS_PER_PAGE);
                          setRecordPage(1);
                        }}
                        data={[
                          { value: '10', label: '10 / page' },
                          { value: '25', label: '25 / page' },
                          { value: '50', label: '50 / page' },
                          { value: '100', label: '100 / page' },
                        ]}
                        allowDeselect={false}
                        size="xs"
                        className="actor-page-size"
                      />
                    </Group>
                  </Group>
                  {recordError ? (
                    <ErrorBlock message={recordError} />
                  ) : loadingRecords ? (
                    <LoadingBlock />
                  ) : records.length === 0 ? (
                    <EmptyState message="No records found for this platform." />
                  ) : (
                    <>
                      <RecordTable records={pageRecords} onOpen={setSelectedRecordId} variant="compact" />
                      <Group justify="space-between" align="center" wrap="nowrap">
                        <Text size="xs" c="dimmed">
                          {recordRangeStart}-{recordRangeEnd} of {records.length}
                        </Text>
                        <Pagination
                          total={totalRecordPages}
                          value={safeRecordPage}
                          onChange={setRecordPage}
                          size="sm"
                          siblings={1}
                          boundaries={1}
                        />
                      </Group>
                    </>
                  )}
                </Stack>
              )}
            </>
          )}
        </Stack>
      </div>
    </Stack>
  );
}
