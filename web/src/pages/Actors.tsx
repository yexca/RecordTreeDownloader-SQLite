import {
  ActionIcon,
  Button,
  Group,
  NumberInput,
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

export default function Actors() {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(50);
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
      const nextActors = await api.actors(query, limit);
      setActors(nextActors);
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
      setRecords(await api.actorRecords(actor.id, limit));
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
              <TextInput
                label="Actor"
                placeholder="Search actor name"
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
              <Group align="end" wrap="nowrap">
                <NumberInput
                  label="Limit"
                  value={limit}
                  min={1}
                  max={500}
                  step={10}
                  onChange={(value) => setLimit(Number(value) || 50)}
                />
                <Button type="submit" leftSection={<IconSearch size={16} />} loading={loadingActors}>
                  Search
                </Button>
                <Tooltip label="Refresh actors">
                  <ActionIcon
                    variant="light"
                    size={36}
                    aria-label="Refresh actors"
                    loading={loadingActors}
                    onClick={() => loadActors()}
                  >
                    <IconRefresh size={16} />
                  </ActionIcon>
                </Tooltip>
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
            <ScrollArea.Autosize mah="calc(100vh - 260px)" type="auto">
              <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Name</Table.Th>
                    <Table.Th className="nowrap">Records</Table.Th>
                    <Table.Th className="nowrap">Undownloaded</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {actors.map((actor) => (
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
