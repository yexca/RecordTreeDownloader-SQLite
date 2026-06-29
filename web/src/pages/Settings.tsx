import { SimpleGrid, Stack, Text, Title } from '@mantine/core';

function PlaceholderBlock({ title, description }: { title: string; description: string }) {
  return (
    <Stack p="md" className="section" gap={4}>
      <Title order={3} size="h4">
        {title}
      </Title>
      <Text size="sm" c="dimmed">
        {description}
      </Text>
    </Stack>
  );
}

export default function Settings() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Settings</Title>
        <Text size="sm" c="dimmed">
          Configure local paths, download defaults, and MEGAcmd integration.
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <PlaceholderBlock
          title="Paths"
          description="This area will manage database, downloads, logs, and upload directories."
        />
        <PlaceholderBlock
          title="Download defaults"
          description="This area will manage safety margin, .par2 defaults, file type defaults, and output behavior."
        />
        <PlaceholderBlock
          title="MEGAcmd"
          description="This area will show executable paths, login state, and setup guidance."
        />
        <PlaceholderBlock
          title="Import preferences"
          description="This area will manage metadata preference and import behavior."
        />
      </SimpleGrid>
    </Stack>
  );
}
