import {
  Alert,
  Button,
  Group,
  PasswordInput,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconLogin, IconLogout, IconRefresh } from '@tabler/icons-react';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { MegaAccountStatus, MegaCommandStatus } from '../api/types';
import { ErrorBlock, LoadingBlock } from '../components/LoadingError';
import { CheckBadge } from '../components/StatusBadge';

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
  const [status, setStatus] = useState<MegaAccountStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authCode, setAuthCode] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    setError(null);
    return api
      .megaStatus()
      .then(setStatus)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    refresh();
  }, []);

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
      notifications.show({ color: 'teal', message: 'MEGAcmd logout completed.' });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (error && !status) return <ErrorBlock message={error} />;
  if (!status) return <LoadingBlock />;

  const canLogin = status.mega_login.available && !busy;
  const canLogout = status.mega_logout.available && !busy;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Settings</Title>
          <Text size="sm" c="dimmed">
            Configure local paths, download defaults, and MEGAcmd integration.
          </Text>
        </div>
        <Button
          variant="light"
          leftSection={<IconRefresh size={16} />}
          onClick={() => refresh()}
          loading={busy}
        >
          Refresh
        </Button>
      </Group>

      {error ? (
        <Alert color="red" title="MEGAcmd operation failed">
          {error}
        </Alert>
      ) : null}

      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <Stack p="md" className="section" gap="md">
          <Group justify="space-between">
            <div>
              <Title order={3} size="h4">
                MEGAcmd Account
              </Title>
              <Text size="sm" c="dimmed">
                Login state is stored by MEGAcmd, not in the RecordTree database.
              </Text>
            </div>
            <CheckBadge value={status.login.logged_in ? 'pass' : 'fail'} />
          </Group>

          <Table withTableBorder verticalSpacing={6} fz="sm">
            <Table.Tbody>
              <Table.Tr>
                <Table.Th className="nowrap">Status</Table.Th>
                <Table.Td>{status.login.logged_in ? 'Logged in' : 'Not logged in'}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Th className="nowrap">Message</Table.Th>
                <Table.Td className="url-cell">{status.login.message}</Table.Td>
              </Table.Tr>
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

        <form onSubmit={submitLogin}>
          <Stack p="md" className="section" gap="md">
            <div>
              <Title order={3} size="h4">
                Login
              </Title>
              <Text size="sm" c="dimmed">
                Password is sent only to MEGAcmd for this login attempt.
              </Text>
            </div>

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
      </SimpleGrid>

      <Stack p="md" className="section">
        <Title order={3} size="h4">
          Commands
        </Title>
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
    </Stack>
  );
}
