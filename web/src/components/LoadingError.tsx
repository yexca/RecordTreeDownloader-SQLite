import { Alert, Loader, Stack } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';

export function LoadingBlock() {
  return (
    <Stack align="center" py="xl">
      <Loader size="sm" />
    </Stack>
  );
}

export function ErrorBlock({ message }: { message: string }) {
  return (
    <Alert color="red" icon={<IconAlertCircle size={18} />} variant="light">
      {message}
    </Alert>
  );
}
