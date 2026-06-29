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
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ActorSummary, RecordSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { RecordTable } from '../components/RecordTable';
import RecordDetail from './RecordDetail';

const ACTOR_FETCH_LIMIT = 500;
const DEFAULT_ACTORS_PER_PAGE = 25;
const RECORD_FETCH_LIMIT = 500;
const DEFAULT_RECORDS_PER_PAGE = 25;
type SearchMode = 'name' | 'id';

export default function Actors() {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('name');
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_ACTORS_PER_PAGE);
  const [recordPage, setRecordPage] = useState(1);
  const [recordsPerPage, setRecordsPerPage] = useState(DEFAULT_RECORDS_PER_PAGE);
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [selectedActor, setSelectedActor] = useState<ActorSummary | null>(null);
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [loadingActors, setLoadingActors] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [actorError, setActorError] = useState<string | null>(null);
  const [recordError, setRecordError] = useState<string | null>(null);

  const loadActors = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoadingActors(true);
    setActorError(null);
    try {
      const id = Number(query.trim());
      const nextActors =
        searchMode === 'id' && Number.isInteger(id) && id > 0
          ? [await api.actor(id)]
          : await api.actors(searchMode === 'name' ? query : '', ACTOR_FETCH_LIMIT);
      setActors(nextActors);
      setPage(1);
      if (selectedActor && !nextActors.some((actor) => actor.id === selectedActor.id)) {
        setSelectedActor(null);
        setRecords([]);
        setSelectedRecordId(null);
      }
    } catch (err) {
      setActorError(err instanceof Error ? err.message : 'Actor search failed');
    } finally {
      setLoadingActors(false);
    }
  };

  const loadActorRecords = async (actor: ActorSummary) => {
    setSelectedActor(actor);
    setSelectedRecordId(null);
    setRecordPage(1);
    setLoadingRecords(true);
    setRecordError(null);
    try {
      setRecords(await api.actorRecords(actor.id, RECORD_FETCH_LIMIT));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Actor records failed';
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
    loadActors();
    // Initial load only; search form and refresh button control later requests.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const trimmedQuery = query.trim();
  const visibleActors =
    searchMode === 'id' && trimmedQuery
      ? actors.filter((actor) => String(actor.id).includes(trimmedQuery))
      : actors;
  const totalPages = Math.max(1, Math.ceil(visibleActors.length / perPage));
  const safePage = Math.min(page, totalPages);
  const pageActors = visibleActors.slice((safePage - 1) * perPage, safePage * perPage);
  const rangeStart = visibleActors.length === 0 ? 0 : (safePage - 1) * perPage + 1;
  const rangeEnd = Math.min(safePage * perPage, visibleActors.length);
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
          <Title order={2}>Actors</Title>
          <Text size="sm" c="dimmed">
            Browse actor directories and open related records.
          </Text>
        </div>
      </Group>

      <div className="actors-layout">
        <Stack className="section actor-directory" gap={0}>
          <form onSubmit={loadActors}>
            <Stack gap="sm" p="md" className="actor-directory-toolbar">
              <Group justify="space-between" align="start" wrap="nowrap">
                <div>
                  <Title order={3} size="h4">
                    Directory
                  </Title>
                  <Text size="xs" c="dimmed">
                    {visibleActors.length} shown, {actors.length} loaded
                  </Text>
                </div>
                <Tooltip label="Refresh actors">
                  <ActionIcon
                    variant="subtle"
                    size={32}
                    aria-label="Refresh actors"
                    loading={loadingActors}
                    onClick={() => loadActors()}
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
                  aria-label="Search actor"
                  placeholder={searchMode === 'id' ? 'Actor ID' : 'Actor name'}
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
                    aria-label="Search actors"
                    loading={loadingActors}
                  >
                    <IconSearch size={16} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Stack>
          </form>

          <div className="actor-directory-body">
            {actorError ? (
              <ErrorBlock message={actorError} />
            ) : loadingActors ? (
              <LoadingBlock />
            ) : actors.length === 0 ? (
              <EmptyState message="No actors found." />
            ) : (
              <ScrollArea.Autosize mah="calc(100vh - 330px)" type="auto">
                <Stack gap={4} p="xs">
                  {pageActors.map((actor) => (
                    <button
                      key={actor.id}
                      type="button"
                      className="actor-list-item"
                      data-selected={selectedActor?.id === actor.id || undefined}
                      onClick={() => loadActorRecords(actor)}
                    >
                      <span className="actor-list-main">
                        <Text size="sm" fw={700} className="truncate-cell" title={actor.name}>
                          {actor.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          ID {actor.id} | {actor.record_count} records
                        </Text>
                      </span>
                      <Badge variant="light" color={actor.undownloaded_count > 0 ? 'yellow' : 'teal'} size="sm">
                        {actor.undownloaded_count}
                      </Badge>
                    </button>
                  ))}
                </Stack>
              </ScrollArea.Autosize>
            )}
          </div>

          {actors.length > 0 && !actorError && (
            <Stack className="actor-directory-footer" gap="xs">
              <Group justify="space-between" align="center" wrap="nowrap">
                <Text size="xs" c="dimmed">
                  {rangeStart}-{rangeEnd} of {visibleActors.length}
                </Text>
                <Select
                  aria-label="Actors per page"
                  value={String(perPage)}
                  onChange={(value) => {
                    setPerPage(Number(value) || DEFAULT_ACTORS_PER_PAGE);
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
          {!selectedActor ? (
            <Stack className="section actor-empty-state" align="center" justify="center" gap="xs">
              <Title order={3} size="h4">
                Select an actor
              </Title>
              <Text size="sm" c="dimmed" ta="center">
                Choose an actor from the directory to review records and download coverage.
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
                        <Badge variant="light">{selectedActor.record_count} records</Badge>
                        <Badge variant="light" color={selectedActor.undownloaded_count > 0 ? 'yellow' : 'teal'}>
                          {selectedActor.undownloaded_count} undownloaded
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
                    <EmptyState message="No records found for this actor." />
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
