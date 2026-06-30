import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Checkbox,
  Collapse,
  Group,
  NumberInput,
  PasswordInput,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import {
  IconChevronDown,
  IconChevronRight,
  IconDeviceFloppy,
  IconLogin,
  IconLogout,
  IconRefresh,
  IconSettings,
} from '@tabler/icons-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { MegaAccountStatus, MegaCommandStatus, SettingsPayload } from '../api/types';
import { CheckBadge } from '../components/StatusBadge';
import { useCachedState } from '../state/pageState';

function CommandRow({ name, command }: { name: string; command: MegaCommandStatus }) {
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

function normalizeTemplate(value: string) {
  return value.trim().replace(/\\/g, '/').replace(/\/{2,}/g, '/').replace(/^\/+|\/+$/g, '');
}

function BasicSettings() {
  const [settings, setSettings] = useCachedState<SettingsPayload | null>('settings.basic', null);
  const [folderTemplate, setFolderTemplate] = useState('');
  const [minimumFreeSpaceGb, setMinimumFreeSpaceGb] = useState<number | string>(10);
  const [safetyMarginPercent, setSafetyMarginPercent] = useState<number | string>(5);
  const [includePar2, setIncludePar2] = useState(false);
  const [loading, setLoading] = useState(settings === null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applySettings = (payload: SettingsPayload) => {
    setSettings(payload);
    setFolderTemplate(payload.download.folder_template);
    setMinimumFreeSpaceGb(payload.download.minimum_free_space_mb / 1024);
    setSafetyMarginPercent(payload.download.safety_margin_percent);
    setIncludePar2(payload.download.include_par2_by_default);
  };

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      applySettings(await api.settings());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Settings failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!settings) void load();
    else applySettings(settings);
    // Initial cache hydration only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const preview = useMemo(() => {
    const template = normalizeTemplate(folderTemplate || '{actor_safe_name}/{record_group_id}');
    return `${settings?.paths.downloads || 'downloads'} / ${template
      .replaceAll('{actor_safe_name}', 'API Actor')
      .replaceAll('{actor}', 'API Actor')
      .replaceAll('{record_group_id}', '123')
      .replaceAll('{source}', 'niconico')
      .replaceAll('{source_key}', 'sample-key')
      .replaceAll('{title_safe}', 'Sample Title')
      .replaceAll('{title}', 'Sample Title')
      .replaceAll('{delivery_date}', '2026-01-02')
      .replaceAll('{entry_date}', '2026-01-03')
      .replaceAll('/', ' / ')}`;
  }, [folderTemplate, settings?.paths.downloads]);

  const insertVariable = (name: string) => {
    const token = `{${name}}`;
    setFolderTemplate((current) => {
      if (!current.trim()) return token;
      return `${current.replace(/\/?$/, '/')}${token}`;
    });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const next = await api.updateSettings({
        download: {
          folder_template: folderTemplate,
          safety_margin_percent: Number(safetyMarginPercent) || 0,
          minimum_free_space_mb: Math.round((Number(minimumFreeSpaceGb) || 0) * 1024),
          include_par2_by_default: includePar2,
        },
      });
      applySettings(next);
      notifications.show({ color: 'teal', message: 'Settings saved.' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Settings save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={3} size="h4">
              Basic
            </Title>
            <Text size="sm" c="dimmed">
              Configure download defaults used by plans and jobs.
            </Text>
          </div>
          <Group gap="xs">
            <Tooltip label="Reload settings">
              <ActionIcon variant="light" aria-label="Reload settings" loading={loading} onClick={() => void load()}>
                <IconRefresh size={16} />
              </ActionIcon>
            </Tooltip>
            <Button type="submit" leftSection={<IconDeviceFloppy size={16} />} loading={saving}>
              Save
            </Button>
          </Group>
        </Group>

        {error ? <Alert color="red">{error}</Alert> : null}

        <Stack p="md" className="section" gap="md">
          <Stack gap={2}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
              Download root
            </Text>
            <Text size="sm" className="url-cell">
              {settings?.paths.downloads || 'downloads'}
            </Text>
            <Text size="xs" c="dimmed">
              Locked to the container downloads mount so completed files stay synced to the host.
            </Text>
          </Stack>
          <TextInput
            label="Folder template"
            description="Relative to the download root. A leading slash is trimmed when saved."
            value={folderTemplate}
            onChange={(event) => setFolderTemplate(event.currentTarget.value)}
            placeholder="{actor_safe_name}/{record_group_id}"
          />
          {settings ? (
            <Group gap="xs">
              {Object.entries(settings.variables).map(([name, help]) => (
                <Tooltip key={name} label={help}>
                  <Badge variant="light" className="click-row" onClick={() => insertVariable(name)}>
                    {`{${name}}`}
                  </Badge>
                </Tooltip>
              ))}
            </Group>
          ) : null}
          <Alert color="blue" title="Preview">
            {preview}
          </Alert>
          <div className="settings-number-grid">
            <NumberInput
              label="Minimum free space"
              description="Downloads only start when enough space remains after the selected files are added."
              suffix=" GB"
              min={0}
              decimalScale={2}
              value={minimumFreeSpaceGb}
              onChange={setMinimumFreeSpaceGb}
            />
            <NumberInput
              label="Safety margin"
              description="Extra percentage buffer added to the selected download size for estimates, temporary files, and MEGAcmd overhead."
              suffix="%"
              min={0}
              value={safetyMarginPercent}
              onChange={setSafetyMarginPercent}
            />
          </div>
          <Group>
            <Checkbox
              label="Include .par2 by default"
              checked={includePar2}
              onChange={(event) => setIncludePar2(event.currentTarget.checked)}
            />
          </Group>
        </Stack>
      </Stack>
    </form>
  );
}

function MegaSettings() {
  const [status, setStatus] = useCachedState<MegaAccountStatus | null>('settings.status', null);
  const [lastCheckedAt, setLastCheckedAt] = useCachedState<string | null>('settings.lastCheckedAt', null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authCode, setAuthCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [advancedOpen, { toggle: toggleAdvanced }] = useDisclosure(false);

  const refresh = async () => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await api.megaStatus());
      setLastCheckedAt(new Date().toLocaleString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'MEGAcmd status check failed');
    } finally {
      setBusy(false);
    }
  };

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const nextStatus = await api.megaLogin({
        email,
        password,
        auth_code: authCode.trim() || null,
      });
      setStatus(nextStatus);
      setLastCheckedAt(new Date().toLocaleString());
      setPassword('');
      setAuthCode('');
      notifications.show({ color: 'teal', message: 'MEGAcmd login completed.' });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    setBusy(true);
    setError(null);
    try {
      const nextStatus = await api.megaLogout();
      setStatus(nextStatus);
      setLastCheckedAt(new Date().toLocaleString());
      notifications.show({ color: 'teal', message: 'MEGAcmd logout completed.' });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loggedIn = status?.login.logged_in ?? false;
  const canLogin = Boolean(status?.mega_login.available) && !busy;
  const canLogout = Boolean(status?.mega_logout.available) && !busy;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={3} size="h4">
            MEGAcmd
          </Title>
          <Text size="sm" c="dimmed">
            Login state is stored by MEGAcmd, not in the RecordTree database.
            {lastCheckedAt ? ` Last synced ${lastCheckedAt}.` : ''}
          </Text>
        </div>
        <Group gap="xs">
          <Badge variant="light" color={status ? (loggedIn ? 'teal' : 'red') : 'gray'}>
            {status ? (loggedIn ? 'Logged in' : 'Not logged in') : 'Not synced'}
          </Badge>
          <Tooltip label="Sync MEGAcmd status">
            <ActionIcon variant="light" aria-label="Sync MEGAcmd status" onClick={() => void refresh()} loading={busy}>
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="MEGAcmd operation failed">
          {error}
        </Alert>
      ) : null}

      {!status ? (
        <Alert color="blue" title="MEGAcmd status not synced">
          Use the sync button to query the local MEGAcmd session.
        </Alert>
      ) : null}

      <Stack p="md" className="section" gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4}>Account</Title>
            <Text size="sm" c="dimmed">
              Password is sent only to MEGAcmd for a login attempt.
            </Text>
          </div>
          {status ? <CheckBadge value={loggedIn ? 'pass' : 'fail'} /> : null}
        </Group>

        {status && loggedIn ? (
          <Stack gap="md">
            <Table withTableBorder verticalSpacing={6} fz="sm">
              <Table.Tbody>
                <Table.Tr>
                  <Table.Th className="nowrap">Status</Table.Th>
                  <Table.Td>Logged in</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Th className="nowrap">Account</Table.Th>
                  <Table.Td className="url-cell">{status.login.message}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Th className="nowrap">Persistent data</Table.Th>
                  <Table.Td className="url-cell">{status.persistence_dir}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>

            <Group justify="flex-end">
              <Button
                variant="light"
                color="red"
                leftSection={<IconLogout size={16} />}
                onClick={logout}
                disabled={!canLogout}
                loading={busy}
              >
                Logout
              </Button>
            </Group>
          </Stack>
        ) : (
          <form onSubmit={submitLogin}>
            <Stack gap="md">
              <TextInput
                label="Email"
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
                autoComplete="username"
                required
              />
              <PasswordInput
                label="Password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
                autoComplete="current-password"
                required
              />
              <TextInput
                label="Two-factor code"
                value={authCode}
                onChange={(event) => setAuthCode(event.currentTarget.value)}
                inputMode="numeric"
              />

              <Group justify="flex-end">
                <Button type="submit" leftSection={<IconLogin size={16} />} disabled={!canLogin} loading={busy}>
                  Login
                </Button>
              </Group>
            </Stack>
          </form>
        )}
      </Stack>

      <Stack p="md" className="section">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4}>Advanced</Title>
            <Text size="sm" c="dimmed">
              MEGAcmd executable paths and container persistence details.
            </Text>
          </div>
          <Button
            variant="subtle"
            leftSection={advancedOpen ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
            onClick={toggleAdvanced}
            disabled={!status}
          >
            {advancedOpen ? 'Hide' : 'Show'}
          </Button>
        </Group>

        <Collapse in={advancedOpen && Boolean(status)}>
          {status ? (
            <Stack gap="md" pt="sm">
              <Table withTableBorder verticalSpacing={6} fz="sm">
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Th className="nowrap">Home</Table.Th>
                    <Table.Td className="url-cell">{status.home_dir}</Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Th className="nowrap">Persistent data</Table.Th>
                    <Table.Td className="url-cell">{status.persistence_dir}</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>

              <div className="table-scroll">
                <Table withTableBorder verticalSpacing={6} fz="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Command</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Resolved path</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    <CommandRow name="mega-get" command={status.mega_get} />
                    <CommandRow name="mega-whoami" command={status.mega_whoami} />
                    <CommandRow name="mega-login" command={status.mega_login} />
                    <CommandRow name="mega-logout" command={status.mega_logout} />
                  </Table.Tbody>
                </Table>
              </div>
            </Stack>
          ) : null}
        </Collapse>
      </Stack>
    </Stack>
  );
}

export default function Settings() {
  return (
    <Stack gap="md" className="settings-shell">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Settings</Title>
          <Text size="sm" c="dimmed">
            Configure download defaults and MEGAcmd integration.
          </Text>
        </div>
      </Group>

      <Tabs defaultValue="basic" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="basic" leftSection={<IconSettings size={16} />}>
            Basic
          </Tabs.Tab>
          <Tabs.Tab value="mega" leftSection={<IconRefresh size={16} />}>
            MEGAcmd
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="basic" pt="md">
          <BasicSettings />
        </Tabs.Panel>
        <Tabs.Panel value="mega" pt="md">
          <MegaSettings />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
