import {
  Alert,
  Button,
  Collapse,
  Group,
  PasswordInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconChevronDown, IconChevronRight, IconLogin, IconLogout, IconRefresh } from '@tabler/icons-react';
import { FormEvent, useState } from 'react';
import { api } from '../api/client';
import type { MegaAccountStatus, MegaCommandStatus } from '../api/types';
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

export default function Settings() {
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
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Settings</Title>
          <Text size="sm" c="dimmed">
            Configure local paths, download defaults, and MEGAcmd integration.
          </Text>
        </div>
        <Button variant="light" leftSection={<IconRefresh size={16} />} onClick={() => void refresh()} loading={busy}>
          Check MEGAcmd
        </Button>
      </Group>

      {error ? (
        <Alert color="red" title="MEGAcmd operation failed">
          {error}
        </Alert>
      ) : null}

      {!status ? (
        <Alert color={error ? 'red' : 'blue'} title={error ? 'MEGAcmd status unavailable' : 'MEGAcmd status not checked'}>
          {error || 'Use Check MEGAcmd to query the local MEGAcmd session. This avoids running MEGAcmd commands just by opening the page.'}
        </Alert>
      ) : null}

      {status ? (
      <Stack p="md" className="section" gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={3} size="h4">
              MEGAcmd Account
            </Title>
            <Text size="sm" c="dimmed">
              Login state is stored by MEGAcmd, not in the RecordTree database.
              {lastCheckedAt ? ` Last checked ${lastCheckedAt}.` : ''}
            </Text>
          </div>
          <CheckBadge value={loggedIn ? 'pass' : 'fail'} />
        </Group>

        {loggedIn ? (
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
              <Text size="sm" c="dimmed">
                Password is sent only to MEGAcmd for this login attempt.
              </Text>

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
      ) : null}

      {status ? (
      <Stack p="md" className="section">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={3} size="h4">
              Advanced
            </Title>
            <Text size="sm" c="dimmed">
              MEGAcmd executable paths and container persistence details.
            </Text>
          </div>
          <Button
            variant="subtle"
            leftSection={advancedOpen ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
            onClick={toggleAdvanced}
          >
            {advancedOpen ? 'Hide' : 'Show'}
          </Button>
        </Group>

        <Collapse in={advancedOpen}>
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
        </Collapse>
      </Stack>
      ) : null}
    </Stack>
  );
}
