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
import { IconRefresh, IconSearch } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { PlatformSummary, RecordSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { RecordTable } from '../components/RecordTable';
import { useCachedState } from '../state/pageState';
import RecordDetail from './RecordDetail';

const DEFAULT_PLATFORMS_PER_PAGE = 25;
const RECORD_FETCH_LIMIT = 500;
const DEFAULT_RECORDS_PER_PAGE = 25;
type SearchMode = 'name' | 'id';

export default function Platform() {
  const [query, setQuery] = useCachedState('platform.query', '');
  const [searchMode, setSearchMode] = useCachedState<SearchMode>('platform.searchMode', 'name');
  const [page, setPage] = useCachedState('platform.page', 1);
  const [perPage, setPerPage] = useCachedState('platform.perPage', DEFAULT_PLATFORMS_PER_PAGE);
  const [recordPage, setRecordPage] = useCachedState('platform.recordPage', 1);
  const [recordsPerPage, setRecordsPerPage] = useCachedState('platform.recordsPerPage', DEFAULT_RECORDS_PER_PAGE);
  const [platforms, setPlatforms] = useCachedState<PlatformSummary[]>('platform.platforms', []);
  const [totalPlatforms, setTotalPlatforms] = useCachedState('platform.totalPlatforms', 0);
  const [totalPlatformPages, setTotalPlatformPages] = useCachedState('platform.totalPlatformPages', 0);
  const [selectedPlatform, setSelectedPlatform] = useCachedState<PlatformSummary | null>('platform.selectedPlatform', null);
  const [records, setRecords] = useCachedState<RecordSummary[]>('platform.records', []);
  const [selectedRecordId, setSelectedRecordId] = useCachedState<number | null>('platform.selectedRecordId', null);
  const [loadingPlatforms, setLoadingPlatforms] = useState(platforms.length === 0);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);
  const [platformError, setPlatformError] = useState<string | null>(null);
  const [recordError, setRecordError] = useState<string | null>(null);

  const loadPlatformPage = async (nextPage = page, nextPerPage = perPage) => {
    setLoadingPlatforms(true);
    setPlatformError(null);
    try {
      const id = Number(query.trim());
      if (searchMode === 'id' && Number.isInteger(id) && id > 0) {
        const nextPlatforms = [await api.platform(id)];
        setPlatforms(nextPlatforms);
        setTotalPlatforms(nextPlatforms.length);
        setTotalPlatformPages(1);
        setPage(1);
        return;
      }
      const result = await api.platformPage(searchMode === 'name' ? query : '', nextPage, nextPerPage);
      setPlatforms(result.items);
      setTotalPlatforms(result.total);
      setTotalPlatformPages(result.total_pages);
      setPage(result.page);
      if (selectedPlatform && !result.items.some((platform) => platform.id === selectedPlatform.id)) {
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
    if (platforms.length === 0) void loadPlatformPage(1);
    // Initial load only; search form and refresh button control later requests.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (platforms.length === 0) return;
    let cancelled = false;
    const refreshCounts = async () => {
      setLoadingCounts(true);
      try {
        const counts = await api.platformUndownloadedCounts(platforms.map((platform) => platform.id));
        if (!cancelled) {
          setPlatforms((current) =>
            current.map((platform) => ({
              ...platform,
              undownloaded_count: counts[String(platform.id)] ?? platform.undownloaded_count,
            })),
          );
          setSelectedPlatform((current) =>
            current
              ? {
                  ...current,
                  undownloaded_count: counts[String(current.id)] ?? current.undownloaded_count,
                }
              : current,
          );
        }
      } catch {
        // Counts are secondary; the main directory stays usable.
      } finally {
        if (!cancelled) setLoadingCounts(false);
      }
    };
    void refreshCounts();
    return () => {
      cancelled = true;
    };
  }, [platforms.map((platform) => platform.id).join(',')]);

  const trimmedQuery = query.trim();
  const visiblePlatforms =
    searchMode === 'id' && trimmedQuery
      ? platforms.filter((platform) => String(platform.id).includes(trimmedQuery))
      : platforms;
  const totalPages = Math.max(1, searchMode === 'id' ? 1 : totalPlatformPages);
  const safePage = Math.min(page, totalPages);
  const pagePlatforms = visiblePlatforms;
  const rangeStart = totalPlatforms === 0 ? 0 : (safePage - 1) * perPage + 1;
  const rangeEnd = Math.min(safePage * perPage, totalPlatforms);
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
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setPage(1);
              void loadPlatformPage(1);
            }}
          >
            <Stack gap="sm" p="md" className="actor-directory-toolbar">
              <Group justify="space-between" align="start" wrap="nowrap">
                <div>
                  <Title order={3} size="h4">
                    Directory
                  </Title>
                  <Text size="xs" c="dimmed">
                    {platforms.length} shown, {totalPlatforms} total{loadingCounts ? ', counts loading' : ''}
                  </Text>
                </div>
                <Tooltip label="Refresh platforms">
                  <ActionIcon
                    variant="subtle"
                    size={32}
                    aria-label="Refresh platforms"
                    loading={loadingPlatforms}
                    onClick={() => loadPlatformPage(page)}
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
                  {rangeStart}-{rangeEnd} of {totalPlatforms}
                </Text>
                <Select
                  aria-label="Platforms per page"
                  value={String(perPage)}
                  onChange={(value) => {
                    const nextPerPage = Number(value) || DEFAULT_PLATFORMS_PER_PAGE;
                    setPerPage(nextPerPage);
                    setPage(1);
                    void loadPlatformPage(1, nextPerPage);
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
                onChange={(nextPage) => {
                  setPage(nextPage);
                  void loadPlatformPage(nextPage);
                }}
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
              {selectedRecordId ? (
                <RecordDetail idOrKey={String(selectedRecordId)} onBack={() => setSelectedRecordId(null)} />
              ) : (
                <Stack p="md" className="section" gap="md">
                  <Group justify="space-between" align="center">
                    <div>
                      <Title order={3} size="h4">
                        Records
                      </Title>
                      <Group gap="xs" mt={4}>
                        <Badge variant="light">{selectedPlatform.record_count} records</Badge>
                        <Badge variant="light" color={selectedPlatform.undownloaded_count > 0 ? 'yellow' : 'teal'}>
                          {selectedPlatform.undownloaded_count} undownloaded
                        </Badge>
                      </Group>
                    </div>
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
