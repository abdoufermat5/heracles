/**
 * Config History Panel
 * ====================
 *
 * Displays configuration change history.
 */

import { format } from "date-fns";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { History, ChevronLeft, ChevronRight } from "lucide-react";
import { useConfigHistory } from "@/hooks/use-config";
import type { ConfigHistoryParams } from "@/types/config";
import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface ConfigHistoryPanelProps {
  entityType?: "setting" | "plugin";
  entityId?: string;
  pageSize?: number;
}

export function ConfigHistoryPanel({
  entityType,
  entityId,
  pageSize = 20,
}: ConfigHistoryPanelProps) {
  const [page, setPage] = useState(0);

  const params: ConfigHistoryParams = {
    entityType,
    entityId,
    limit: pageSize,
    offset: page * pageSize,
  };

  const { data, isLoading, error } = useConfigHistory(params);

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

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

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Configuration History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">
            Failed to load history: {error.message}
          </p>
        </CardContent>
      </Card>
    );
  }

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
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : !data?.items?.length ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No configuration changes recorded yet.
          </p>
        ) : (
          <>
            <div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Setting</TableHead>
                    <TableHead>Old Value</TableHead>
                    <TableHead>New Value</TableHead>
                    <TableHead>Changed By</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="whitespace-nowrap text-sm">
                        {format(new Date(entry.changedAt), "MMM d, yyyy HH:mm")}
                      </TableCell>
                      <TableCell>
                        <Badge variant={entry.pluginName ? "secondary" : "outline"}>
                          {entry.pluginName ? "plugin" : "setting"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {entry.pluginName || entry.category}/{entry.settingKey}
                      </TableCell>
                      <TableCell className="max-w-[150px]">
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">
                          {truncateValue(formatValue(entry.oldValue))}
                        </code>
                      </TableCell>
                      <TableCell className="max-w-[150px]">
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">
                          {truncateValue(formatValue(entry.newValue))}
                        </code>
                      </TableCell>
                      <TableCell className="text-sm">
                        {entry.changedBy}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">
                  Showing {page * pageSize + 1}-
                  {Math.min((page + 1) * pageSize, data?.total || 0)} of{" "}
                  {data?.total || 0} entries
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
