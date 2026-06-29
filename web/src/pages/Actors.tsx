import {
  ActionIcon,
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
            Browse actors and inspect their record groups.
          </Text>
        </div>
      </Group>

      <div className="split-layout">
        <Stack p="md" className="section split-pane" gap="sm">
          <form onSubmit={loadActors}>
            <Stack gap="sm">
              <Group justify="space-between" align="center">
                <Title order={3} size="h4">
                  Actor Search
                </Title>
                <Tooltip label="Refresh actors">
                  <ActionIcon
                    variant="light"
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
                label="Actor"
                placeholder="Search actor name"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
              <Group justify="space-between" align="center">
                <Text size="xs" c="dimmed">
                  Showing 25 actors per page
                </Text>
                <Button type="submit" leftSection={<IconSearch size={16} />} loading={loadingActors}>
                  Search
                </Button>
              </Group>
            </Stack>
          </form>

          {actorError ? (
            <ErrorBlock message={actorError} />
          ) : loadingActors ? (
            <LoadingBlock />
          ) : actors.length === 0 ? (
            <EmptyState message="No actors found." />
          ) : (
            <>
              <ScrollArea.Autosize mah="calc(100vh - 330px)" type="auto">
                <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Name</Table.Th>
                      <Table.Th className="nowrap">Records</Table.Th>
                      <Table.Th className="nowrap">Undownloaded</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {pageActors.map((actor) => (
                      <Table.Tr
                        key={actor.id}
                        className="click-row"
                        data-selected={selectedActor?.id === actor.id || undefined}
                        onClick={() => loadActorRecords(actor)}
                      >
                        <Table.Td>
                          <Text size="sm" fw={600} className="truncate-cell" title={actor.name}>
                            {actor.name}
                          </Text>
                        </Table.Td>
                        <Table.Td className="nowrap">{actor.record_count}</Table.Td>
                        <Table.Td className="nowrap">{actor.undownloaded_count}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea.Autosize>

              <Group justify="space-between" align="center" wrap="nowrap">
                <Text size="xs" c="dimmed">
                  {rangeStart}-{rangeEnd} of {actors.length}
                </Text>
                <Pagination
                  total={totalPages}
                  value={page}
                  onChange={setPage}
                  size="sm"
                  siblings={1}
                  boundaries={1}
                />
              </Group>
            </>
          )}
        </Stack>

        <Stack p="md" className="section split-pane" gap="md">
          {!selectedActor ? (
            <EmptyState message="Select an actor to view records." />
          ) : selectedRecordId ? (
            <RecordDetail idOrKey={String(selectedRecordId)} onBack={() => setSelectedRecordId(null)} />
          ) : (
            <>
              <Group justify="space-between" align="start">
                <div>
                  <Title order={3} size="h4">
                    {selectedActor.name}
                  </Title>
                  <Text size="sm" c="dimmed">
                    {selectedActor.record_count} records, {selectedActor.undownloaded_count} undownloaded
                  </Text>
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

              {recordError ? (
                <ErrorBlock message={recordError} />
              ) : loadingRecords ? (
                <LoadingBlock />
              ) : records.length === 0 ? (
                <EmptyState message="No records found for this actor." />
              ) : (
                <RecordTable records={records} onOpen={setSelectedRecordId} />
              )}
            </>
          )}
        </Stack>
      </div>
    </Stack>
  );
}
