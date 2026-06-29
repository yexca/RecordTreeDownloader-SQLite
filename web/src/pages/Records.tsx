import { Stack, Text, Title } from '@mantine/core';

export default function Records() {
  return (
    <Stack gap="md">
      <div>
        <Title order={2}>Records</Title>
        <Text size="sm" c="dimmed">
          Browse and filter record groups.
        </Text>
      </div>

      <Stack p="md" className="section" gap={4}>
        <Title order={3} size="h4">
          Record browser
        </Title>
        <Text size="sm" c="dimmed">
          This page will provide combined filters for actor, title, platform, date range, file type, and
          download status.
        </Text>
      </Stack>
    </Stack>
  );
}
