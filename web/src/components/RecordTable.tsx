import { ActionIcon, Group, Table, Text, Tooltip } from '@mantine/core';
import { IconExternalLink } from '@tabler/icons-react';
import type { RecordSummary } from '../api/types';
import { DownloadedBadge } from './StatusBadge';
import { formatBytes, formatText } from './format';

export function RecordTable({
  records,
  onOpen,
}: {
  records: RecordSummary[];
  onOpen: (recordId: number) => void;
}) {
  return (
    <div className="table-scroll">
      <Table striped highlightOnHover withTableBorder verticalSpacing={6} fz="sm">
        <Table.Thead>
          <Table.Tr>
            <Table.Th className="nowrap">ID</Table.Th>
            <Table.Th>Title</Table.Th>
            <Table.Th>Actor</Table.Th>
            <Table.Th>Source</Table.Th>
            <Table.Th className="nowrap">Delivery</Table.Th>
            <Table.Th className="nowrap">Links</Table.Th>
            <Table.Th className="nowrap">Size</Table.Th>
            <Table.Th className="nowrap">Status</Table.Th>
            <Table.Th className="nowrap" />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {records.map((record) => (
            <Table.Tr key={record.id} className="click-row" onClick={() => onOpen(record.id)}>
              <Table.Td className="nowrap">{record.id}</Table.Td>
              <Table.Td>
                <Text size="sm" fw={600} className="truncate-cell" title={record.title}>
                  {record.title}
                </Text>
              </Table.Td>
              <Table.Td className="truncate-cell">{formatText(record.actor)}</Table.Td>
              <Table.Td className="truncate-cell">{formatText(record.source)}</Table.Td>
              <Table.Td className="nowrap">{formatText(record.delivery_date)}</Table.Td>
              <Table.Td className="nowrap">
                {record.completed_links}/{record.active_links}
              </Table.Td>
              <Table.Td className="nowrap">{formatBytes(record.size_bytes)}</Table.Td>
              <Table.Td className="nowrap">
                <DownloadedBadge value={record.downloaded} />
              </Table.Td>
              <Table.Td className="nowrap">
                <Group justify="flex-end">
                  <Tooltip label="Open record">
                    <ActionIcon
                      variant="subtle"
                      aria-label="Open record"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpen(record.id);
                      }}
                    >
                      <IconExternalLink size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  );
}
