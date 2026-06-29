import { Button, Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { IconSettings } from '@tabler/icons-react';
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
  const megaChecks = useMemo(
    () =>
      doctor?.checks.filter((check) =>
        ['mega-whoami', 'mega-get', 'mega_login'].includes(check.name),
      ) ?? [],
    [doctor],
  );
  const failingChecks = doctor?.checks.filter((check) => check.status === 'fail') ?? [];
  const warningChecks = doctor?.checks.filter((check) => check.status === 'warn') ?? [];

  if (error) return <ErrorBlock message={error} />;
  if (!doctor) return <LoadingBlock />;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>System Status</Title>
          <Text size="sm" c="dimmed">
            Read-only diagnostics for local runtime, paths, and MEGAcmd.
          </Text>
        </div>
        <Group>
          <Button
            component="a"
            href="#/settings"
            variant="light"
            leftSection={<IconSettings size={16} />}
          >
            Open Settings
          </Button>
          <CheckBadge value={doctor.ok ? 'pass' : 'fail'} />
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Stack p="md" className="section" gap={4}>
          <Text size="sm" c="dimmed">
            Overall
          </Text>
          <Group justify="space-between">
            <Text fw={700}>{doctor.ok ? 'Healthy' : 'Needs attention'}</Text>
            <CheckBadge value={doctor.ok ? 'pass' : 'fail'} />
          </Group>
        </Stack>
        <Stack p="md" className="section" gap={4}>
          <Text size="sm" c="dimmed">
            Failures
          </Text>
          <Text fw={700}>{failingChecks.length}</Text>
        </Stack>
        <Stack p="md" className="section" gap={4}>
          <Text size="sm" c="dimmed">
            Warnings
          </Text>
          <Text fw={700}>{warningChecks.length}</Text>
        </Stack>
      </SimpleGrid>

      {megaChecks.length ? (
        <Stack p="md" className="section">
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={3} size="h4">
                MEGAcmd
              </Title>
              <Text size="sm" c="dimmed">
                Runtime command availability and login status.
              </Text>
            </div>
            <Button component="a" href="#/settings" variant="subtle" leftSection={<IconSettings size={16} />}>
              Manage
            </Button>
          </Group>
          <div className="table-scroll">
            <Table withTableBorder verticalSpacing={6} fz="sm">
              <Table.Tbody>
                {megaChecks.map((check) => (
                  <Table.Tr key={check.name}>
                    <Table.Th className="nowrap">{check.name}</Table.Th>
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
      ) : null}

      <Stack p="md" className="section">
        <Title order={3} size="h4">
          Doctor Checks
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
