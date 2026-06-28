import { Group, Stack, Table, Text, Title } from '@mantine/core';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { DoctorResult } from '../api/types';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { CheckBadge } from '../components/StatusBadge';

export default function SystemStatus() {
  const [doctor, setDoctor] = useState<DoctorResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .doctor()
      .then(setDoctor)
      .catch((err: Error) => setError(err.message));
  }, []);

  const pathChecks = useMemo(
    () =>
      doctor?.checks.filter((check) =>
        ['config', 'database', 'downloads_dir', 'logs_dir'].includes(check.name),
      ) ?? [],
    [doctor],
  );

  if (error) return <ErrorBlock message={error} />;
  if (!doctor) return <LoadingBlock />;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>System Status</Title>
          <Text size="sm" c="dimmed">
            Doctor checks and local paths
          </Text>
        </div>
        <CheckBadge value={doctor.ok ? 'pass' : 'fail'} />
      </Group>

      <Stack p="md" className="section">
        <Title order={3} size="h4">
          Checks
        </Title>
        <div className="table-scroll">
          <Table striped withTableBorder verticalSpacing={6} fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Message</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {doctor.checks.map((check) => (
                <Table.Tr key={check.name}>
                  <Table.Td className="nowrap">{check.name}</Table.Td>
                  <Table.Td className="nowrap">
                    <CheckBadge value={check.status} />
                  </Table.Td>
                  <Table.Td className="url-cell">{check.message}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </Stack>

      <Stack p="md" className="section">
        <Title order={3} size="h4">
          Paths
        </Title>
        <div className="table-scroll">
          <Table withTableBorder verticalSpacing={6} fz="sm">
            <Table.Tbody>
              {pathChecks.map((check) => (
                <Table.Tr key={check.name}>
                  <Table.Th className="nowrap">{check.name}</Table.Th>
                  <Table.Td className="url-cell">{check.message}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </Stack>
    </Stack>
  );
}
