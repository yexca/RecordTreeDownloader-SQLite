import { Alert, Text } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';

export function EmptyState({ message }: { message: string }) {
  return (
    <Alert icon={<IconInfoCircle size={18} />} color="gray" variant="light">
      <Text size="sm">{message}</Text>
    </Alert>
  );
}
