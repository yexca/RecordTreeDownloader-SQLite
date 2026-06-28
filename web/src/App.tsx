import {
  AppShell,
  Burger,
  Group,
  NavLink,
  Text,
  Tooltip,
  UnstyledButton,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure, useHash } from '@mantine/hooks';
import {
  IconDatabase,
  IconLayoutDashboard,
  IconMoon,
  IconSearch,
  IconSettings,
  IconSun,
} from '@tabler/icons-react';
import Dashboard from './pages/Dashboard';
import RecordDetail from './pages/RecordDetail';
import Search from './pages/Search';
import SystemStatus from './pages/SystemStatus';

type Route = 'dashboard' | 'search' | 'status' | 'record';

function parseHash(hash: string): { route: Route; recordId?: string } {
  const normalized = hash.replace(/^#\/?/, '');
  const [route, recordId] = normalized.split('/');
  if (route === 'search') return { route: 'search' };
  if (route === 'status') return { route: 'status' };
  if (route === 'records' && recordId) return { route: 'record', recordId };
  return { route: 'dashboard' };
}

export default function App() {
  const [opened, { toggle, close }] = useDisclosure();
  const [hash, setHash] = useHash();
  const { route, recordId } = parseHash(hash);
  const { colorScheme, setColorScheme } = useMantineColorScheme();

  const navigate = (target: string) => {
    setHash(target);
    close();
  };

  const page =
    route === 'search' ? (
      <Search onOpenRecord={(id) => navigate(`/records/${id}`)} />
    ) : route === 'status' ? (
      <SystemStatus />
    ) : route === 'record' && recordId ? (
      <RecordDetail idOrKey={recordId} onBack={() => navigate('/search')} />
    ) : (
      <Dashboard onOpenRecord={(id) => navigate(`/records/${id}`)} />
    );

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <IconDatabase size={24} color="#0f766e" />
            <Text className="app-title">RecordTree WebUI</Text>
          </Group>
          <Tooltip label="Toggle color scheme">
            <UnstyledButton
              aria-label="Toggle color scheme"
              onClick={() => setColorScheme(colorScheme === 'dark' ? 'light' : 'dark')}
            >
              {colorScheme === 'dark' ? <IconSun size={20} /> : <IconMoon size={20} />}
            </UnstyledButton>
          </Tooltip>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <NavLink
          label="Dashboard"
          leftSection={<IconLayoutDashboard size={18} />}
          active={route === 'dashboard'}
          onClick={() => navigate('/')}
        />
        <NavLink
          label="Search"
          leftSection={<IconSearch size={18} />}
          active={route === 'search' || route === 'record'}
          onClick={() => navigate('/search')}
        />
        <NavLink
          label="System Status"
          leftSection={<IconSettings size={18} />}
          active={route === 'status'}
          onClick={() => navigate('/status')}
        />
      </AppShell.Navbar>

      <AppShell.Main>{page}</AppShell.Main>
    </AppShell>
  );
}
