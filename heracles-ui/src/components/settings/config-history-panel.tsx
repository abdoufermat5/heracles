/**
 * Config History Panel
 * ====================
 *
 * Displays configuration change history using the shared DataTable component.
 */

import { useMemo } from "react";
import { format } from "date-fns";
import { type ColumnDef } from "@tanstack/react-table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { History } from "lucide-react";
import { DataTable, SortableHeader } from "@/components/common";
import { useConfigHistory } from "@/hooks/use-config";
import type { ConfigHistoryEntry, ConfigHistoryParams } from "@/types/config";

interface ConfigHistoryPanelProps {
  entityType?: "setting" | "plugin";
  entityId?: string;
  pageSize?: number;
}

// Helper functions
const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "(empty)";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
};

const truncateValue = (value: string, maxLength = 50): string => {
  if (value.length <= maxLength) return value;
  return value.substring(0, maxLength) + "...";
};

export function ConfigHistoryPanel({
  entityType,
  entityId,
  pageSize = 20,
}: ConfigHistoryPanelProps) {
  const params: ConfigHistoryParams = {
    entityType,
    entityId,
    limit: 100, // Fetch more for client-side pagination
    offset: 0,
  };

  const { data, isLoading, error } = useConfigHistory(params);

  // Define columns for the DataTable
  const columns = useMemo<ColumnDef<ConfigHistoryEntry>[]>(
    () => [
      {
        accessorKey: "changedAt",
        header: ({ column }) => (
          <SortableHeader column={column}>Date</SortableHeader>
        ),
        cell: ({ row }) => (
          <span className="whitespace-nowrap text-sm">
            {format(new Date(row.original.changedAt), "MMM d, yyyy HH:mm")}
          </span>
        ),
        size: 150,
      },
      {
        id: "type",
        header: "Type",
        cell: ({ row }) => (
          <Badge variant={row.original.pluginName ? "secondary" : "outline"}>
            {row.original.pluginName ? "plugin" : "setting"}
          </Badge>
        ),
        size: 80,
        enableSorting: false,
      },
      {
        id: "setting",
        header: ({ column }) => (
          <SortableHeader column={column}>Setting</SortableHeader>
        ),
        accessorFn: (row) =>
          `${row.pluginName || row.category || ""}/${row.settingKey || ""}`,
        cell: ({ row }) => (
          <span className="font-mono text-sm">
            {row.original.pluginName || row.original.category}/
            {row.original.settingKey}
          </span>
        ),
        size: 200,
      },
      {
        accessorKey: "oldValue",
        header: "Old Value",
        cell: ({ row }) => (
          <code className="text-xs bg-muted px-1 py-0.5 rounded">
            {truncateValue(formatValue(row.original.oldValue))}
          </code>
        ),
        size: 150,
        enableSorting: false,
      },
      {
        accessorKey: "newValue",
        header: "New Value",
        cell: ({ row }) => (
          <code className="text-xs bg-muted px-1 py-0.5 rounded">
            {truncateValue(formatValue(row.original.newValue))}
          </code>
        ),
        size: 150,
        enableSorting: false,
      },
      {
        accessorKey: "changedBy",
        header: ({ column }) => (
          <SortableHeader column={column}>Changed By</SortableHeader>
        ),
        cell: ({ row }) => {
          // Extract username from DN if present
          const changedBy = row.original.changedBy;
          const match = changedBy.match(/uid=([^,]+)/);
          return (
            <span className="text-sm" title={changedBy}>
              {match ? match[1] : changedBy}
            </span>
          );
        },
        size: 120,
      },
      {
        accessorKey: "reason",
        header: "Reason",
        cell: ({ row }) =>
          row.original.reason ? (
            <span className="text-sm text-muted-foreground">
              {truncateValue(row.original.reason, 30)}
            </span>
          ) : (
            <span className="text-muted-foreground">-</span>
          ),
        size: 150,
        enableSorting: false,
      },
    ],
    []
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          Configuration History
        </CardTitle>
        <CardDescription>
          Track all configuration changes made to the system
        </CardDescription>
      </CardHeader>
      <CardContent>
        <DataTable
          columns={columns}
          data={data?.items || []}
          isLoading={isLoading}
          error={error}
          emptyMessage="No configuration changes recorded"
          emptyDescription="Configuration changes will appear here once you start modifying settings."
          enableSearch
          searchPlaceholder="Search history..."
          searchColumn="setting"
          enablePagination
          defaultPageSize={pageSize}
          pageSizes={[10, 20, 50]}
          dense
          getRowId={(row: ConfigHistoryEntry) => row.id}
        />
      </CardContent>
    </Card>
  );
}
