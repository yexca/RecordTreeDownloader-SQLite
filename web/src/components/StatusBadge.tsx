import { Badge } from '@mantine/core';
import type { CheckStatus, DownloadedStatus } from '../api/types';

const downloadedColors: Record<DownloadedStatus, string> = {
  all: 'teal',
  partial: 'yellow',
  none: 'gray',
  unknown: 'red',
};

const checkColors: Record<CheckStatus, string> = {
  pass: 'teal',
  warn: 'yellow',
  fail: 'red',
};

export function DownloadedBadge({ value }: { value: DownloadedStatus }) {
  return (
    <Badge color={downloadedColors[value] ?? 'gray'} variant="light" size="sm">
      {value}
    </Badge>
  );
}

export function CheckBadge({ value }: { value: CheckStatus }) {
  return (
    <Badge color={checkColors[value] ?? 'gray'} variant="light" size="sm">
      {value}
    </Badge>
  );
}

export function PlainStatusBadge({ value }: { value: string }) {
  const color = value.includes('fail')
    ? 'red'
    : value.includes('complete')
      ? 'teal'
      : value.includes('block') || value.includes('cancel')
        ? 'yellow'
        : 'gray';
  return (
    <Badge color={color} variant="light" size="sm">
      {value}
    </Badge>
  );
}
