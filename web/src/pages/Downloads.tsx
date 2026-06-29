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

export default function Downloads() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Downloads</Title>
        <Text size="sm" c="dimmed">
          Track download jobs and history.
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <PlaceholderBlock
          title="Active jobs"
          description="This area will show queued and running import or download jobs with progress."
        />
        <PlaceholderBlock
          title="Download history"
          description="This area will show completed, failed, blocked, and cancelled downloads."
        />
      </SimpleGrid>
    </Stack>
  );
}
