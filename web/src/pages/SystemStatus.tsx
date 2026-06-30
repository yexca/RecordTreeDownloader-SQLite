import { Button, Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDatabaseExport, IconDownload, IconRefresh, IconSettings, IconStethoscope } from '@tabler/icons-react';
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type {
  BackupSummary,
  IntegrityResult,
  MaintenanceActionResult,
  MaintenanceSummary,
  MegaAccountStatus,
  MegaCommandStatus,
  OrphanReport,
} from '../api/types';
import { CheckBadge } from '../components/StatusBadge';
import { formatBytes } from '../components/format';
import { useCachedState } from '../state/pageState';

type ActionResult =
  | { kind: 'backup'; title: string; result: BackupSummary }
  | { kind: 'integrity'; title: string; result: IntegrityResult }
  | { kind: 'orphans'; title: string; result: OrphanReport }
  | { kind: 'analyze'; title: string; result: MaintenanceActionResult }
  | { kind: 'vacuum'; title: string; result: MaintenanceActionResult };

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
  const [summary, setSummary] = useCachedState<MaintenanceSummary | null>('maintenance.summary', null);
  const [lastCheckedAt, setLastCheckedAt] = useCachedState<string | null>('maintenance.lastCheckedAt', null);
  const [megaStatus, setMegaStatus] = useCachedState<MegaAccountStatus | null>('maintenance.megaStatus', null);
  const [megaCheckedAt, setMegaCheckedAt] = useCachedState<string | null>('maintenance.megaCheckedAt', null);
  const [error, setError] = useState<string | null>(null);
  const [megaError, setMegaError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [lastResult, setLastResult] = useCachedState<ActionResult | null>('maintenance.lastResult', null);

  const loadSummary = async () => {
    setError(null);
    try {
      setSummary(await api.maintenanceSummary());
      setLastCheckedAt(new Date().toLocaleString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const refreshSummary = async () => {
    setBusy('refresh');
    try {
      await loadSummary();
    } finally {
      setBusy(null);
    }
  };

  useEffect(() => {
    if (!summary && busy !== 'refresh') void refreshSummary();
    // Load local maintenance summary once; it does not invoke MEGAcmd.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshMegaStatus = async () => {
    setBusy('mega');
    setMegaError(null);
    try {
      setMegaStatus(await api.megaStatus());
      setMegaCheckedAt(new Date().toLocaleString());
    } catch (err) {
      setMegaError(err instanceof Error ? err.message : 'MEGAcmd status check failed');
    } finally {
      setBusy(null);
    }
  };

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
      summary?.checks.filter((check) =>
        ['config', 'database', 'downloads_dir', 'logs_dir'].includes(check.name),
      ) ?? [],
    [summary],
  );
  const failingChecks = summary?.checks.filter((check) => check.status === 'fail') ?? [];
  const warningChecks = summary?.checks.filter((check) => check.status === 'warn') ?? [];

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Maintenance</Title>
          <Text size="sm" c="dimmed">
            Local paths, database health, backups, and explicit MEGAcmd checks.
            {lastCheckedAt ? ` Last local refresh ${lastCheckedAt}.` : ''}
          </Text>
        </div>
        <Group>
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            onClick={() => void refreshSummary()}
            loading={busy === 'refresh'}
          >
            Refresh Local
          </Button>
          {summary ? <CheckBadge value={summary.ok ? 'pass' : 'fail'} /> : null}
        </Group>
      </Group>

      {error ? (
        <Stack p="md" className="section">
          <Text c="red" fw={700}>
            Diagnostics failed
          </Text>
          <Text size="sm">{error}</Text>
        </Stack>
      ) : null}

      {!summary ? (
        <Stack p="md" className="section">
          <Text size="sm" c="dimmed">
            Loading local maintenance summary...
          </Text>
        </Stack>
      ) : (
      <>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
        <Metric label="Local status" value={summary.ok ? 'Healthy' : 'Needs attention'} status={summary.ok ? 'pass' : 'fail'} />
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
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
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
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            loading={busy === 'vacuum'}
            onClick={() =>
              void runAction('vacuum', 'Vacuum database', async () => ({
                kind: 'vacuum',
                title: 'Vacuum database',
                result: await api.maintenanceVacuum(),
              }))
            }
          >
            Vacuum database
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

      <BackupTable backups={summary.backups} />

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <CheckTable title="Paths" checks={pathChecks} />
        <MegaPanel
          status={megaStatus}
          error={megaError}
          checkedAt={megaCheckedAt}
          loading={busy === 'mega'}
          onRefresh={() => void refreshMegaStatus()}
        />
      </SimpleGrid>
      </>
      )}
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

function MegaPanel({
  status,
  error,
  checkedAt,
  loading,
  onRefresh,
}: {
  status: MegaAccountStatus | null;
  error: string | null;
  checkedAt: string | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <Stack p="md" className="section">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={3} size="h4">
            MEGAcmd
          </Title>
          <Text size="sm" c="dimmed">
            {checkedAt ? `Last checked ${checkedAt}.` : 'Not checked.'}
          </Text>
        </div>
        <Button variant="light" leftSection={<IconRefresh size={16} />} loading={loading} onClick={onRefresh}>
          Check MEGAcmd
        </Button>
      </Group>
      {error ? (
        <Text size="sm" c="red">
          {error}
        </Text>
      ) : null}
      {!status ? (
        <Text size="sm" c="dimmed">
          Use Check MEGAcmd to query command availability and login state.
        </Text>
      ) : (
        <div className="table-scroll">
          <Table withTableBorder verticalSpacing={6} fz="sm">
            <Table.Tbody>
              <Table.Tr>
                <Table.Th className="nowrap">Login</Table.Th>
                <Table.Td className="nowrap">
                  <CheckBadge value={status.login.logged_in ? 'pass' : 'fail'} />
                </Table.Td>
                <Table.Td className="url-cell">{status.login.message}</Table.Td>
              </Table.Tr>
              <MegaCommandRow name="mega-get" command={status.mega_get} />
              <MegaCommandRow name="mega-whoami" command={status.mega_whoami} />
              <MegaCommandRow name="mega-login" command={status.mega_login} />
              <MegaCommandRow name="mega-logout" command={status.mega_logout} />
            </Table.Tbody>
          </Table>
        </div>
      )}
    </Stack>
  );
}

function MegaCommandRow({ name, command }: { name: string; command: MegaCommandStatus }) {
  return (
    <Table.Tr>
      <Table.Th className="nowrap">{name}</Table.Th>
      <Table.Td className="nowrap">
        <CheckBadge value={command.available ? 'pass' : 'fail'} />
      </Table.Td>
      <Table.Td className="url-cell">{command.resolved || command.message}</Table.Td>
    </Table.Tr>
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
            ['Download', backupDownloadUrl(action.result.path)],
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

function BackupTable({ backups }: { backups: BackupSummary[] }) {
  return (
    <Stack p="md" className="section">
      <Group justify="space-between">
        <Title order={3} size="h4">
          Backup History
        </Title>
        <Text size="sm" c="dimmed">
          {backups.length} backup{backups.length === 1 ? '' : 's'}
        </Text>
      </Group>
      {backups.length === 0 ? (
        <Text size="sm" c="dimmed">
          No database backups have been created yet.
        </Text>
      ) : (
        <div className="table-scroll">
          <Table striped withTableBorder verticalSpacing={6} fz="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>File</Table.Th>
                <Table.Th className="nowrap">Size</Table.Th>
                <Table.Th className="nowrap">Created</Table.Th>
                <Table.Th className="nowrap" />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {backups.map((backup) => (
                <Table.Tr key={backup.path}>
                  <Table.Td className="url-cell">{backup.path}</Table.Td>
                  <Table.Td className="nowrap">{formatBytes(backup.size_bytes)}</Table.Td>
                  <Table.Td className="nowrap">{backup.created_at}</Table.Td>
                  <Table.Td className="nowrap">
                    <Button
                      component="a"
                      href={backupDownloadUrl(backup.path)}
                      download
                      variant="subtle"
                      size="xs"
                      leftSection={<IconDownload size={14} />}
                    >
                      Download
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
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
              <Table.Td className="url-cell">
                {key === 'Download' ? (
                  <Button component="a" href={value} download variant="subtle" size="xs" leftSection={<IconDownload size={14} />}>
                    Download backup
                  </Button>
                ) : (
                  value
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  );
}

function backupDownloadUrl(path: string) {
  const normalized = path.replaceAll('\\', '/');
  const filename = normalized.split('/').pop() ?? '';
  return `/api/maintenance/backups/${encodeURIComponent(filename)}`;
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
