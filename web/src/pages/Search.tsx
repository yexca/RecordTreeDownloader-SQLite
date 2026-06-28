import {
  Button,
  Group,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconSearch } from '@tabler/icons-react';
import { FormEvent, useState } from 'react';
import { api } from '../api/client';
import type { ActorSummary, RecordSummary } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { RecordTable } from '../components/RecordTable';

type Mode = 'title' | 'actor' | 'source' | 'date' | 'undownloaded';

export default function Search({ onOpenRecord }: { onOpenRecord: (id: number) => void }) {
  const [mode, setMode] = useState<Mode>('title');
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<RecordSummary[]>([]);
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [searched, setSearched] = useState(false);

  const runSearch = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoading(true);
    setSearched(true);
    try {
      setActors([]);
      setRecords([]);
      if (mode === 'actor') {
        setActors(await api.actors(query, limit));
      } else if (mode === 'source') {
        setRecords(await api.searchSource(query, limit));
      } else if (mode === 'date') {
        setRecords(await api.searchDate(from, to, limit));
      } else if (mode === 'undownloaded') {
        setRecords(await api.undownloaded(query, source, limit));
      } else {
        setRecords(await api.searchTitle(query, limit));
      }
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Search failed',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const showQuery = mode === 'title' || mode === 'actor' || mode === 'source' || mode === 'undownloaded';

  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Search</Title>
        <Text size="sm" c="dimmed">
          Find actors and record groups
        </Text>
      </div>

      <form onSubmit={runSearch}>
        <Stack p="md" className="section" gap="sm">
          <Group grow align="end">
            <Select
              label="Mode"
              value={mode}
              onChange={(value) => setMode((value as Mode | null) ?? 'title')}
              data={[
                { value: 'title', label: 'Title' },
                { value: 'actor', label: 'Actor' },
                { value: 'source', label: 'Source' },
                { value: 'date', label: 'Date range' },
                { value: 'undownloaded', label: 'Undownloaded' },
              ]}
            />
            {showQuery && (
              <TextInput
                label={mode === 'undownloaded' ? 'Actor filter' : 'Query'}
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
            )}
            {mode === 'undownloaded' && (
              <TextInput
                label="Source filter"
                value={source}
                onChange={(event) => setSource(event.currentTarget.value)}
              />
            )}
            {mode === 'date' && (
              <>
                <TextInput label="From" placeholder="YYYY-MM-DD" value={from} onChange={(e) => setFrom(e.currentTarget.value)} />
                <TextInput label="To" placeholder="YYYY-MM-DD" value={to} onChange={(e) => setTo(e.currentTarget.value)} />
              </>
            )}
            <NumberInput
              label="Limit"
              value={limit}
              min={1}
              max={500}
              step={10}
              onChange={(value) => setLimit(Number(value) || 50)}
            />
            <Button type="submit" leftSection={<IconSearch size={16} />} loading={loading}>
              Search
            </Button>
          </Group>
        </Stack>
      </form>

      <Stack p="md" className="section">
        {mode === 'actor' ? (
          actors.length === 0 ? (
            <EmptyState message={searched ? 'No actors found.' : 'Run a search to see actor results.'} />
          ) : (
            <div className="table-scroll">
              <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Name</Table.Th>
                    <Table.Th>Records</Table.Th>
                    <Table.Th>Undownloaded</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {actors.map((actor) => (
                    <Table.Tr key={actor.id}>
                      <Table.Td>{actor.id}</Table.Td>
                      <Table.Td>{actor.name}</Table.Td>
                      <Table.Td>{actor.record_count}</Table.Td>
                      <Table.Td>{actor.undownloaded_count}</Table.Td>
                      <Table.Td>
                        <Button
                          size="compact-sm"
                          variant="subtle"
                          onClick={async () => {
                            setLoading(true);
                            try {
                              setRecords(await api.actorRecords(actor.id, limit));
                              setActors([]);
                            } finally {
                              setLoading(false);
                            }
                          }}
                        >
                          Records
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )
        ) : records.length === 0 ? (
          <EmptyState message={searched ? 'No records found.' : 'Run a search to see record results.'} />
        ) : (
          <RecordTable records={records} onOpen={onOpenRecord} />
        )}

        {mode === 'actor' && records.length > 0 && <RecordTable records={records} onOpen={onOpenRecord} />}
      </Stack>
    </Stack>
  );
}
