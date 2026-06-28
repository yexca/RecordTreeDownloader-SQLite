import { Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { StatsResult } from '../api/types';
import { EmptyState } from '../components/EmptyState';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { PlainStatusBadge } from '../components/StatusBadge';
import { formatBytes } from '../components/format';

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <Stack gap={2} p="md" className="section">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text size="xl" fw={700}>
        {value}
      </Text>
    </Stack>
  );
}

export default function Dashboard({ onOpenRecord }: { onOpenRecord: (id: number) => void }) {
  const [stats, setStats] = useState<StatsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <ErrorBlock message={error} />;
  if (!stats) return <LoadingBlock />;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Dashboard</Title>
          <Text size="sm" c="dimmed">
            Local SQLite overview
          </Text>
        </div>
      </Group>

      <SimpleGrid cols={{ base: 2, md: 5 }}>
        <Metric label="Record groups" value={stats.total_record_groups} />
        <Metric label="Active links" value={stats.active_link_count} />
        <Metric label="Inactive links" value={stats.inactive_link_count} />
        <Metric label="Actors" value={stats.actor_count} />
        <Metric label="Sources" value={stats.source_count} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Metric label="Downloaded all" value={stats.downloaded_all} />
        <Metric label="Partial" value={stats.downloaded_partial} />
        <Metric label="None" value={stats.downloaded_none} />
        <Metric label="Unknown" value={stats.downloaded_unknown} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Stack p="md" className="section">
          <Title order={3} size="h4">
            Recent Imports
          </Title>
          {stats.recent_imports.length === 0 ? (
            <EmptyState message="No imports recorded yet." />
          ) : (
            <div className="table-scroll">
              <Table striped withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>File</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Rows</Table.Th>
                    <Table.Th>Errors</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {stats.recent_imports.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td>{item.id}</Table.Td>
                      <Table.Td className="truncate-cell" title={item.source_file_name}>
                        {item.source_file_name}
                      </Table.Td>
                      <Table.Td>
                        <PlainStatusBadge value={item.status} />
                      </Table.Td>
                      <Table.Td>{item.total_rows}</Table.Td>
                      <Table.Td>{item.error_count}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )}
        </Stack>

        <Stack p="md" className="section">
          <Title order={3} size="h4">
            Recent Downloads
          </Title>
          {stats.recent_downloads.length === 0 ? (
            <EmptyState message="No downloads recorded yet." />
          ) : (
            <div className="table-scroll">
              <Table striped withTableBorder verticalSpacing={6} fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Record</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Bytes</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {stats.recent_downloads.map((item) => (
                    <Table.Tr
                      key={item.id}
                      className="click-row"
                      onClick={() => onOpenRecord(item.record_group_id)}
                    >
                      <Table.Td>{item.id}</Table.Td>
                      <Table.Td>{item.record_group_id}</Table.Td>
                      <Table.Td>
                        <PlainStatusBadge value={item.status} />
                      </Table.Td>
                      <Table.Td>{formatBytes(item.selected_bytes)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
          )}
        </Stack>
      </SimpleGrid>
    </Stack>
  );
}
