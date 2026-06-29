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

export default function Actors() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Actors</Title>
        <Text size="sm" c="dimmed">
          Browse actors and inspect their record groups.
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <PlaceholderBlock
          title="Actor list"
          description="This area will show searchable actors with record counts and undownloaded counts."
        />
        <PlaceholderBlock
          title="Actor records"
          description="Select an actor to show related records, then open a record detail from here."
        />
      </SimpleGrid>
    </Stack>
  );
}
