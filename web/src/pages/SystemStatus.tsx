import { Button, Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDatabaseExport, IconRefresh, IconSettings, IconStethoscope } from '@tabler/icons-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type {
  BackupSummary,
  IntegrityResult,
  MaintenanceActionResult,
  MaintenanceSummary,
  OrphanReport,
} from '../api/types';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { CheckBadge } from '../components/StatusBadge';
import { formatBytes } from '../components/format';

type ActionResult =
  | { kind: 'backup'; title: string; result: BackupSummary }
  | { kind: 'integrity'; title: string; result: IntegrityResult }
  | { kind: 'orphans'; title: string; result: OrphanReport }
  | { kind: 'analyze'; title: string; result: MaintenanceActionResult };

const orphanLabels: Record<keyof Omit<OrphanReport, 'ok'>, string> = {
  actors_without_records: 'Actors without records',
  sources_without_records: 'Sources without records',
  record_actor_orphans: 'Broken record actor mappings',
  record_source_orphans: 'Broken record source mappings',
  links_without_record: 'Links without records',
  downloads_without_record: 'Downloads without records',
  download_items_without_download: 'Download items without downloads',
  download_items_without_link: 'Download items without links',
};

export default function SystemStatus() {
  const [summary, setSummary] = useState<MaintenanceSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ActionResult | null>(null);

  const loadSummary = async () => {
    setError(null);
    try {
      setSummary(await api.maintenanceSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  useEffect(() => {
    void loadSummary();
  }, []);

  const runAction = async (kind: string, title: string, action: () => Promise<ActionResult>) => {
    setBusy(kind);
    try {
      const result = await action();
      setLastResult(result);
      notifications.show({ color: 'teal', title, message: 'Maintenance action completed.' });
      await loadSummary();
    } catch (err) {
      notifications.show({
        color: 'red',
        title,
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setBusy(null);
    }
  };

  const pathChecks = useMemo(
    () =>
      summary?.doctor.checks.filter((check) =>
        ['config', 'database', 'downloads_dir', 'logs_dir'].includes(check.name),
      ) ?? [],
    [summary],
  );
  const megaChecks = useMemo(
    () =>
      summary?.doctor.checks.filter((check) =>
        ['mega-whoami', 'mega-get', 'mega_login'].includes(check.name),
      ) ?? [],
    [summary],
  );
  const failingChecks = summary?.doctor.checks.filter((check) => check.status === 'fail') ?? [];
  const warningChecks = summary?.doctor.checks.filter((check) => check.status === 'warn') ?? [];

  if (error) return <ErrorBlock message={error} />;
  if (!summary) return <LoadingBlock />;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Maintenance</Title>
          <Text size="sm" c="dimmed">
            Diagnostics, database backup, integrity checks, and local runtime maintenance.
          </Text>
        </div>
        <Group>
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={() => void loadSummary()}
            loading={busy === 'refresh'}
          >
            Run Diagnostics
          </Button>
          <CheckBadge value={summary.doctor_ok ? 'pass' : 'fail'} />
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
        <Metric label="Overall" value={summary.doctor_ok ? 'Healthy' : 'Needs attention'} status={summary.doctor_ok ? 'pass' : 'fail'} />
        <Metric label="Failures" value={failingChecks.length} />
        <Metric label="Warnings" value={warningChecks.length} />
        <Metric label="Database" value={formatBytes(summary.database_size_bytes)} />
        <Metric label="Latest backup" value={summary.latest_backup ? formatBytes(summary.latest_backup.size_bytes) : 'None'} />
      </SimpleGrid>

      <Stack p="md" className="section" gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={3} size="h4">
              Database Maintenance
            </Title>
            <Text size="sm" c="dimmed">
              Safe operations for local SQLite data and query metadata.
            </Text>
          </div>
          <Button component="a" href="#/settings" variant="subtle" leftSection={<IconSettings size={16} />}>
            Settings
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          <Button
            variant="light"
            leftSection={<IconDatabaseExport size={16} />}
            loading={busy === 'backup'}
            onClick={() =>
              void runAction('backup', 'Backup database', async () => ({
                kind: 'backup',
                title: 'Backup database',
                result: await api.maintenanceBackup(),
              }))
            }
          >
            Backup database
          </Button>
          <Button
            variant="light"
            leftSection={<IconStethoscope size={16} />}
            loading={busy === 'integrity'}
            onClick={() =>
              void runAction('integrity', 'Integrity check', async () => ({
                kind: 'integrity',
                title: 'Integrity check',
                result: await api.maintenanceIntegrity(),
              }))
            }
          >
            Check integrity
          </Button>
          <Button
            variant="light"
            leftSection={<IconStethoscope size={16} />}
            loading={busy === 'orphans'}
            onClick={() =>
              void runAction('orphans', 'Orphan data check', async () => ({
                kind: 'orphans',
                title: 'Orphan data check',
                result: await api.maintenanceOrphans(),
              }))
            }
          >
            Check orphans
          </Button>
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            loading={busy === 'analyze'}
            onClick={() =>
              void runAction('analyze', 'Analyze database', async () => ({
                kind: 'analyze',
                title: 'Analyze database',
                result: await api.maintenanceAnalyze(),
              }))
            }
          >
            Analyze database
          </Button>
        </SimpleGrid>
        <div className="table-scroll">
          <Table withTableBorder verticalSpacing={6} fz="sm">
            <Table.Tbody>
              <Table.Tr>
                <Table.Th className="nowrap">Database path</Table.Th>
                <Table.Td className="url-cell">{summary.database_path}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Th className="nowrap">Backup directory</Table.Th>
                <Table.Td className="url-cell">{summary.backup_dir}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Th className="nowrap">Latest backup</Table.Th>
                <Table.Td className="url-cell">
                  {summary.latest_backup ? summary.latest_backup.path : 'No backup has been created yet.'}
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </div>
      </Stack>

      {lastResult ? <ResultPanel action={lastResult} /> : null}

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <CheckTable title="Paths" checks={pathChecks} />
        <CheckTable title="MEGAcmd" checks={megaChecks} />
      </SimpleGrid>

      <CheckTable title="Doctor Checks" checks={summary.doctor.checks} striped />
    </Stack>
  );
}

function Metric({ label, value, status }: { label: string; value: number | string; status?: 'pass' | 'warn' | 'fail' }) {
  return (
    <Stack p="md" className="section" gap={4}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Group justify="space-between" wrap="nowrap">
        <Text fw={700}>{value}</Text>
        {status ? <CheckBadge value={status} /> : null}
      </Group>
    </Stack>
  );
}

function CheckTable({ title, checks, striped = false }: { title: string; checks: { name: string; status: 'pass' | 'warn' | 'fail'; message: string }[]; striped?: boolean }) {
  return (
    <Stack p="md" className="section">
      <Title order={3} size="h4">
        {title}
      </Title>
      <div className="table-scroll">
        <Table striped={striped} withTableBorder verticalSpacing={6} fz="sm">
          <Table.Tbody>
            {checks.map((check) => (
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
  );
}

function ResultPanel({ action }: { action: ActionResult }) {
  return (
    <Stack p="md" className="section">
      <Group justify="space-between">
        <Title order={3} size="h4">
          Last Result
        </Title>
        <Text size="sm" c="dimmed">
          {action.title}
        </Text>
      </Group>
      {action.kind === 'backup' ? (
        <KeyValueTable
          rows={[
            ['Path', action.result.path],
            ['Size', formatBytes(action.result.size_bytes)],
            ['Created', action.result.created_at],
          ]}
        />
      ) : action.kind === 'integrity' ? (
        <CheckTable title="Integrity Result" checks={action.result.checks} />
      ) : action.kind === 'orphans' ? (
        <OrphanTable report={action.result} />
      ) : (
        <KeyValueTable
          rows={[
            ['Status', action.result.ok ? 'Completed' : 'Failed'],
            ['Message', action.result.message],
            ['Started', action.result.started_at],
            ['Finished', action.result.finished_at],
          ]}
        />
      )}
    </Stack>
  );
}

function KeyValueTable({ rows }: { rows: [string, string][] }) {
  return (
    <div className="table-scroll">
      <Table withTableBorder verticalSpacing={6} fz="sm">
        <Table.Tbody>
          {rows.map(([key, value]) => (
            <Table.Tr key={key}>
              <Table.Th className="nowrap">{key}</Table.Th>
              <Table.Td className="url-cell">{value}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  );
}

function OrphanTable({ report }: { report: OrphanReport }) {
  const rows = Object.entries(orphanLabels).map(([key, label]) => {
    const value = report[key as keyof typeof orphanLabels];
    return [label, String(value), value === 0 ? 'pass' : 'warn'] as const;
  });
  return (
    <div className="table-scroll">
      <Table withTableBorder verticalSpacing={6} fz="sm">
        <Table.Tbody>
          {rows.map(([label, value, status]) => (
            <Table.Tr key={label}>
              <Table.Th>{label}</Table.Th>
              <Table.Td className="nowrap">
                <CheckBadge value={status} />
              </Table.Td>
              <Table.Td className="nowrap">{value}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  );
}
