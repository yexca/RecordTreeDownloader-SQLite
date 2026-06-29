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

export default function Platform() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Platform</Title>
        <Text size="sm" c="dimmed">
          Browse records by source platform.
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <PlaceholderBlock
          title="Platform list"
          description="This area will show platforms from the source mapping table with record totals."
        />
        <PlaceholderBlock
          title="Platform records"
          description="Select a platform to review matching records and download coverage."
        />
      </SimpleGrid>
    </Stack>
  );
}
