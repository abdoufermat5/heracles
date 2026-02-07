/**
 * SSH Keys Table Component
 *
 * Reusable table for displaying SSH keys using DataTable.
 */

import { useMemo, useState } from 'react'
import { Key, Trash2, Copy, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import {
  DataTable,
  SortableHeader,
  type ColumnDef,
} from '@/components/common/data-table'

import type { SSHKeyRead } from '@/types/ssh'
import { getKeyTypeName, getKeyStrengthVariant, truncateFingerprint } from '@/types/ssh'

interface SshKeysTableProps {
  keys: SSHKeyRead[]
  isLoading?: boolean
  onDelete?: (key: SSHKeyRead) => void
  emptyMessage?: string
}

export function SshKeysTable({
  keys,
  isLoading = false,
  onDelete,
  emptyMessage = 'No SSH keys configured',
}: SshKeysTableProps) {
  const [copiedFingerprint, setCopiedFingerprint] = useState<string | null>(null)

  const copyFingerprint = (fingerprint: string) => {
    navigator.clipboard.writeText(fingerprint)
    setCopiedFingerprint(fingerprint)
    setTimeout(() => setCopiedFingerprint(null), 2000)
  }

  const columns = useMemo<ColumnDef<SSHKeyRead>[]>(
    () => [
      {
        accessorKey: 'keyType',
        header: ({ column }) => (
          <SortableHeader column={column}>Type</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge variant="outline">{getKeyTypeName(row.original.keyType)}</Badge>
        ),
      },
      {
        accessorKey: 'fingerprint',
        header: 'Fingerprint',
        cell: ({ row }) => (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                    {truncateFingerprint(row.original.fingerprint)}
                  </code>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => {
                      e.stopPropagation()
                      copyFingerprint(row.original.fingerprint)
                    }}
                  >
                    {copiedFingerprint === row.original.fingerprint ? (
                      <Check className="h-3 w-3 text-green-500" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                    <span className="sr-only">Copy fingerprint</span>
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-mono text-xs">{row.original.fingerprint}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'comment',
        header: 'Comment',
        cell: ({ row }) => (
          <span className="text-muted-foreground">
            {row.original.comment || '—'}
          </span>
        ),
      },
      {
        accessorKey: 'bits',
        header: ({ column }) => (
          <SortableHeader column={column}>Strength</SortableHeader>
        ),
        cell: ({ row }) => (
          <Badge
            variant={getKeyStrengthVariant(row.original.keyType, row.original.bits)}
          >
            {row.original.bits ? `${row.original.bits} bits` : 'N/A'}
          </Badge>
        ),
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) =>
          onDelete && (
            <div className="flex items-center justify-end">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(row.original)
                }}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete key</span>
              </Button>
            </div>
          ),
        enableSorting: false,
        size: 80,
      },
    ],
    [copiedFingerprint, onDelete]
  )

  return (
    <DataTable
      columns={columns}
      data={keys}
      isLoading={isLoading}
      getRowId={(row) => row.fingerprint}
      emptyMessage={emptyMessage}
      emptyDescription="Add a public key to enable SSH authentication"
      emptyIcon={<Key className="h-8 w-8 text-muted-foreground" />}
      dense
      enableSearch
      searchPlaceholder="Search fingerprints..."
      searchColumn="fingerprint"
      enablePagination
      defaultPageSize={10}
      enableSelection
      enableColumnVisibility
      enableExport
      exportFilename="ssh-keys"
    />
  )
}
