import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Pagination,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconRefresh, IconSearch } from '@tabler/icons-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ActorSummary, RecordSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { RecordTable } from '../components/RecordTable';
import RecordDetail from './RecordDetail';

const ACTOR_FETCH_LIMIT = 500;
const ACTORS_PER_PAGE = 25;
const RECORD_FETCH_LIMIT = 500;

export default function Actors() {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
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
      const nextActors = await api.actors(query, ACTOR_FETCH_LIMIT);
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

  const totalPages = Math.max(1, Math.ceil(actors.length / ACTORS_PER_PAGE));
  const pageActors = actors.slice((page - 1) * ACTORS_PER_PAGE, page * ACTORS_PER_PAGE);
  const rangeStart = actors.length === 0 ? 0 : (page - 1) * ACTORS_PER_PAGE + 1;
  const rangeEnd = Math.min(page * ACTORS_PER_PAGE, actors.length);

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
                    {actors.length} loaded, 25 per page
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
              <TextInput
                aria-label="Search actor"
                placeholder="Search actor name"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
                leftSection={<IconSearch size={16} />}
              />
              <Group justify="end">
                <Button type="submit" loading={loadingActors}>
                  Search
                </Button>
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
                          {actor.record_count} records
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
            <Group className="actor-directory-footer" justify="space-between" align="center" wrap="nowrap">
              <Text size="xs" c="dimmed">
                {rangeStart}-{rangeEnd} of {actors.length}
              </Text>
              <Pagination
                total={totalPages}
                value={page}
                onChange={setPage}
                size="xs"
                siblings={0}
                boundaries={1}
              />
            </Group>
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
          ) : selectedRecordId ? (
            <RecordDetail idOrKey={String(selectedRecordId)} onBack={() => setSelectedRecordId(null)} />
          ) : (
            <>
              <Group className="section actor-summary" justify="space-between" align="start" wrap="nowrap">
                <div>
                  <Title order={3} size="h4">
                    {selectedActor.name}
                  </Title>
                  <Group gap="xs" mt={4}>
                    <Badge variant="light">{selectedActor.record_count} records</Badge>
                    <Badge variant="light" color={selectedActor.undownloaded_count > 0 ? 'yellow' : 'teal'}>
                      {selectedActor.undownloaded_count} undownloaded
                    </Badge>
                  </Group>
                </div>
                <Button
                  variant="subtle"
                  leftSection={<IconArrowLeft size={16} />}
                  onClick={() => {
                    setSelectedActor(null);
                    setRecords([]);
                    setSelectedRecordId(null);
                  }}
                >
                  Clear
                </Button>
              </Group>

              <Stack p="md" className="section" gap="md">
                <Group justify="space-between" align="center">
                  <Title order={3} size="h4">
                    Records
                  </Title>
                  <Text size="xs" c="dimmed">
                    Sorted by delivery date
                  </Text>
                </Group>
                {recordError ? (
                  <ErrorBlock message={recordError} />
                ) : loadingRecords ? (
                  <LoadingBlock />
                ) : records.length === 0 ? (
                  <EmptyState message="No records found for this actor." />
                ) : (
                  <RecordTable records={records} onOpen={setSelectedRecordId} />
                )}
              </Stack>
            </>
          )}
        </Stack>
      </div>
    </Stack>
  );
}
