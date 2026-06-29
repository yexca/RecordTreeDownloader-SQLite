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
  IconDownload,
  IconFileDatabase,
  IconFileImport,
  IconMicrophone2,
  IconLayoutDashboard,
  IconMoon,
  IconPlayerPlay,
  IconSearch,
  IconSettings,
  IconSun,
} from '@tabler/icons-react';
import Actors from './pages/Actors';
import Dashboard from './pages/Dashboard';
import Downloads from './pages/Downloads';
import ImportPage from './pages/Import';
import Platform from './pages/Platform';
import RecordDetail from './pages/RecordDetail';
import Records from './pages/Records';
import Search from './pages/Search';
import Settings from './pages/Settings';
import SystemStatus from './pages/SystemStatus';

type Route =
  | 'dashboard'
  | 'search'
  | 'actors'
  | 'platform'
  | 'records'
  | 'import'
  | 'downloads'
  | 'settings'
  | 'status'
  | 'search-record'
  | 'record';

function parseHash(hash: string): { route: Route; recordId?: string } {
  const normalized = hash.replace(/^#\/?/, '');
  const [route, section, recordId] = normalized.split('/');
  if (route === 'search' && section === 'records' && recordId) return { route: 'search-record', recordId };
  if (route === 'search') return { route: 'search' };
  if (route === 'actors') return { route: 'actors' };
  if (route === 'platform') return { route: 'platform' };
  if (route === 'records' && !section) return { route: 'records' };
  if (route === 'import') return { route: 'import' };
  if (route === 'downloads') return { route: 'downloads' };
  if (route === 'settings') return { route: 'settings' };
  if (route === 'status') return { route: 'status' };
  if (route === 'records' && section) return { route: 'record', recordId: section };
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
      <Search onOpenRecord={(id) => navigate(`/search/records/${id}`)} />
    ) : route === 'actors' ? (
      <Actors />
    ) : route === 'platform' ? (
      <Platform />
    ) : route === 'records' ? (
      <Records onOpenRecord={(id) => navigate(`/records/${id}`)} />
    ) : route === 'import' ? (
      <ImportPage />
    ) : route === 'downloads' ? (
      <Downloads />
    ) : route === 'settings' ? (
      <Settings />
    ) : route === 'status' ? (
      <SystemStatus />
    ) : route === 'record' && recordId ? (
      <RecordDetail idOrKey={recordId} onBack={() => navigate('/records')} />
    ) : route === 'search-record' && recordId ? (
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
          active={route === 'search' || route === 'search-record'}
          onClick={() => navigate('/search')}
        />
        <NavLink
          label="Actors"
          leftSection={<IconMicrophone2 size={18} />}
          active={route === 'actors'}
          onClick={() => navigate('/actors')}
        />
        <NavLink
          label="Platform"
          leftSection={<IconPlayerPlay size={18} />}
          active={route === 'platform'}
          onClick={() => navigate('/platform')}
        />
        <NavLink
          label="Records"
          leftSection={<IconFileDatabase size={18} />}
          active={route === 'records' || route === 'record'}
          onClick={() => navigate('/records')}
        />
        <NavLink
          label="Import"
          leftSection={<IconFileImport size={18} />}
          active={route === 'import'}
          onClick={() => navigate('/import')}
        />
        <NavLink
          label="Downloads"
          leftSection={<IconDownload size={18} />}
          active={route === 'downloads'}
          onClick={() => navigate('/downloads')}
        />
        <NavLink
          label="Settings"
          leftSection={<IconSettings size={18} />}
          active={route === 'settings'}
          onClick={() => navigate('/settings')}
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
