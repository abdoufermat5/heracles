/**
 * DataTable Component
 *
 * A powerful, reusable data table with sorting, pagination, selection,
 * and excellent UX. Built on @tanstack/react-table.
 */

import { useEffect, useMemo, useState } from 'react'
import {
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type PaginationState,
  type ColumnFiltersState,
  type VisibilityState,
  type Row,
  type Table,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  useReactTable,
} from '@tanstack/react-table'
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Settings2,
  Loader2,
  Inbox,
  Download,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table as UITable,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { exportToCsv, exportToJson } from '@/lib/export'
import { useTablePreferencesStore } from '@/stores'

// ============================================================================
// Types
// ============================================================================

export interface DataTableProps<TData, TValue> {
  /** Column definitions */
  columns: ColumnDef<TData, TValue>[]
  /** Data to display */
  data: TData[]
  /** Unique key for each row */
  getRowId?: (row: TData) => string
  /** Loading state */
  isLoading?: boolean
  /** Error state */
  error?: Error | null
  /** Empty state message */
  emptyMessage?: string
  /** Empty state description */
  emptyDescription?: string
  /** Empty state icon */
  emptyIcon?: React.ReactNode
  /** Enable row selection */
  enableSelection?: boolean
  /** Enable global search */
  enableSearch?: boolean
  /** Search placeholder */
  searchPlaceholder?: string
  /** Search column key (for filtering) */
  searchColumn?: string
  /** Enable column visibility toggle */
  enableColumnVisibility?: boolean
  /** Enable pagination */
  enablePagination?: boolean
  /** Page sizes available */
  pageSizes?: number[]
  /** Default page size */
  defaultPageSize?: number
  /** Callback when selection changes */
  onSelectionChange?: (rows: TData[]) => void
  /** Callback when row is clicked */
  onRowClick?: (row: TData) => void
  /** Custom row className */
  rowClassName?: (row: Row<TData>) => string
  /** Header actions (render next to search) */
  headerActions?: React.ReactNode
  /** Bulk actions (shown when rows selected) */
  bulkActions?: (rows: TData[]) => React.ReactNode
  /** Enable export buttons */
  enableExport?: boolean
  /** Export filename prefix */
  exportFilename?: string
  /** Footer content */
  footer?: React.ReactNode
  /** Table className */
  className?: string
  /** Dense mode (compact rows) */
  dense?: boolean
  /** Sticky header */
  stickyHeader?: boolean
  /** Max height for scrollable table */
  maxHeight?: string
}

// ============================================================================
// Helper: Selection Column
// ============================================================================

export function createSelectColumn<TData>(): ColumnDef<TData, unknown> {
  return {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && 'indeterminate')
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
        className="translate-y-[2px]"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
        className="translate-y-[2px]"
        onClick={(e) => e.stopPropagation()}
      />
    ),
    enableSorting: false,
    enableHiding: false,
    size: 40,
  }
}

// ============================================================================
// Helper: Sortable Header
// ============================================================================

interface SortableHeaderProps {
  column: {
    getIsSorted: () => false | 'asc' | 'desc'
    toggleSorting: (desc?: boolean) => void
    getCanSort: () => boolean
  }
  children: React.ReactNode
  className?: string
}

export function SortableHeader({
  column,
  children,
  className,
}: SortableHeaderProps) {
  if (!column.getCanSort()) {
    return <span className={className}>{children}</span>
  }

  const sorted = column.getIsSorted()

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn('-ml-3 h-8 data-[state=open]:bg-accent', className)}
      onClick={() => column.toggleSorting(sorted === 'asc')}
    >
      {children}
      {sorted === 'asc' ? (
        <ArrowUp className="ml-2 h-4 w-4" />
      ) : sorted === 'desc' ? (
        <ArrowDown className="ml-2 h-4 w-4" />
      ) : (
        <ArrowUpDown className="ml-2 h-4 w-4 opacity-50" />
      )}
    </Button>
  )
}

// ============================================================================
// Empty State
// ============================================================================

interface EmptyStateProps {
  message: string
  description?: string
  icon?: React.ReactNode
}

function EmptyState({ message, description, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        {icon ?? <Inbox className="h-8 w-8 text-muted-foreground" />}
      </div>
      <h3 className="text-lg font-medium">{message}</h3>
      {description && (
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">
          {description}
        </p>
      )}
    </div>
  )
}

// ============================================================================
// Pagination (inline to avoid generic issues)
// ============================================================================

interface PaginationControlsProps {
  pageIndex: number
  pageCount: number
  pageSize: number
  totalRows: number
  selectedCount: number
  pageSizes: number[]
  canPreviousPage: boolean
  canNextPage: boolean
  onPageChange: (index: number) => void
  onPageSizeChange: (size: number) => void
  onPreviousPage: () => void
  onNextPage: () => void
}

function PaginationControls({
  pageIndex,
  pageCount,
  totalRows,
  selectedCount,
  pageSizes,
  pageSize,
  canPreviousPage,
  canNextPage,
  onPageChange,
  onPageSizeChange,
  onPreviousPage,
  onNextPage,
}: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="flex-1 text-sm text-muted-foreground">
        {selectedCount > 0 && <span>{selectedCount} of </span>}
        {totalRows} row{totalRows !== 1 ? 's' : ''}
      </div>
      <div className="flex items-center gap-6 lg:gap-8">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">Rows per page</p>
          <Select
            value={`${pageSize}`}
            onValueChange={(value) => onPageSizeChange(Number(value))}
          >
            <SelectTrigger className="h-8 w-[70px]">
              <SelectValue placeholder={pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {pageSizes.map((size) => (
                <SelectItem key={size} value={`${size}`}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex w-[100px] items-center justify-center text-sm font-medium">
          Page {pageIndex + 1} of {pageCount || 1}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            className="hidden h-8 w-8 p-0 lg:flex"
            onClick={() => onPageChange(0)}
            disabled={!canPreviousPage}
          >
            <span className="sr-only">Go to first page</span>
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            className="h-8 w-8 p-0"
            onClick={onPreviousPage}
            disabled={!canPreviousPage}
          >
            <span className="sr-only">Go to previous page</span>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            className="h-8 w-8 p-0"
            onClick={onNextPage}
            disabled={!canNextPage}
          >
            <span className="sr-only">Go to next page</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            className="hidden h-8 w-8 p-0 lg:flex"
            onClick={() => onPageChange(pageCount - 1)}
            disabled={!canNextPage}
          >
            <span className="sr-only">Go to last page</span>
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Column Visibility Menu
// ============================================================================

interface ColumnVisibilityMenuProps<TData> {
  table: Table<TData>
  density?: 'compact' | 'comfortable'
  onDensityChange?: (density: 'compact' | 'comfortable') => void
}

function ColumnVisibilityMenu<TData>({
  table,
  density,
  onDensityChange,
}: ColumnVisibilityMenuProps<TData>) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="h-9">
          <Settings2 className="mr-2 h-4 w-4" />
          View
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[150px]">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {table
          .getAllColumns()
          .filter(
            (column) =>
              typeof column.accessorFn !== 'undefined' && column.getCanHide()
          )
          .map((column) => {
            return (
              <DropdownMenuCheckboxItem
                key={column.id}
                className="capitalize"
                checked={column.getIsVisible()}
                onCheckedChange={(value) => column.toggleVisibility(!!value)}
              >
                {column.id}
              </DropdownMenuCheckboxItem>
            )
          })}
        {onDensityChange && density && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Density</DropdownMenuLabel>
            <DropdownMenuCheckboxItem
              checked={density === 'compact'}
              onCheckedChange={(value) =>
                onDensityChange(value ? 'compact' : 'comfortable')
              }
            >
              Compact rows
            </DropdownMenuCheckboxItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ============================================================================
// Main DataTable Component
// ============================================================================

export function DataTable<TData, TValue>({
  columns,
  data,
  getRowId,
  isLoading = false,
  error = null,
  emptyMessage = 'No results found',
  emptyDescription,
  emptyIcon,
  enableSelection = false,
  enableSearch = false,
  searchPlaceholder = 'Search...',
  searchColumn,
  enableColumnVisibility = false,
  enablePagination = true,
  pageSizes = [10, 20, 30, 50, 100],
  defaultPageSize = 10,
  onRowClick,
  rowClassName,
  headerActions,
  bulkActions,
  enableExport = false,
  exportFilename = 'export',
  onSelectionChange,
  footer,
  className,
  dense: denseProp,
  stickyHeader = false,
  maxHeight,
}: DataTableProps<TData, TValue>) {
  // State
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [globalFilter, setGlobalFilter] = useState('')
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: defaultPageSize,
  })
  const { density, setDensity } = useTablePreferencesStore()
  const dense = denseProp ?? density === 'compact'

  // Build columns with selection if enabled
  const finalColumns = enableSelection
    ? [createSelectColumn<TData>(), ...columns]
    : columns

  // Table instance
  const table = useReactTable({
    data,
    columns: finalColumns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
      pagination,
    },
    enableRowSelection: enableSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    getRowId,
  })

  const selectedRows = table.getFilteredSelectedRowModel().rows
  const selectedData = useMemo(
    () => selectedRows.map((row) => row.original),
    [selectedRows]
  )

  useEffect(() => {
    if (onSelectionChange) {
      onSelectionChange(selectedData)
    }
  }, [onSelectionChange, selectedData])

  // Handle error state
  if (error) {
    return (
      <div className="rounded-md border p-8 text-center">
        <div className="text-destructive mb-2">Error loading data</div>
        <p className="text-sm text-muted-foreground">{error.message}</p>
      </div>
    )
  }

  // Show header if search or column visibility is enabled
  const showHeader =
    enableSearch || enableColumnVisibility || headerActions || enableExport || bulkActions

  const exportRows = () => {
    const rowsToExport = selectedRows.length > 0
      ? selectedRows
      : table.getFilteredRowModel().rows
    const columnsToExport = table
      .getVisibleLeafColumns()
      .filter((column) => {
        if (column.id === 'select') return false
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const def = column.columnDef as any
        return def.accessorKey || def.accessorFn
      })

    const data = rowsToExport.map((row) => {
      const entry: Record<string, unknown> = {}
      for (const column of columnsToExport) {
        entry[column.id] = row.getValue(column.id)
      }
      return entry
    })

    return {
      columns: columnsToExport.map((column) => column.id),
      data,
    }
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header: Search + Actions */}
      {showHeader && (
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-1 items-center gap-2">
            {enableSearch && (
              <div className="relative max-w-sm">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  value={
                    searchColumn
                      ? (table.getColumn(searchColumn)?.getFilterValue() as string) ?? ''
                      : globalFilter
                  }
                  onChange={(event) => {
                    const value = event.target.value
                    if (searchColumn) {
                      table.getColumn(searchColumn)?.setFilterValue(value)
                    } else {
                      setGlobalFilter(value)
                    }
                  }}
                  className="h-9 w-[250px] pl-8 lg:w-[300px]"
                />
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {bulkActions && selectedData.length > 0 && bulkActions(selectedData)}
            {enableExport && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="h-9">
                    <Download className="mr-2 h-4 w-4" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>
                    {selectedRows.length > 0 ? `${selectedRows.length} selected` : 'All results'}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => {
                      const { data, columns } = exportRows()
                      exportToCsv({ data, columns, filename: `${exportFilename}.csv` })
                    }}
                  >
                    Export CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => {
                      const { data } = exportRows()
                      exportToJson({ data, filename: `${exportFilename}.json` })
                    }}
                  >
                    Export JSON
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            {headerActions}
            {enableColumnVisibility && (
              <ColumnVisibilityMenu
                table={table}
                density={density}
                onDensityChange={setDensity}
              />
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div
        className={cn(
          'rounded-md border',
          maxHeight && 'overflow-auto',
          stickyHeader && '[&_thead]:sticky [&_thead]:top-0 [&_thead]:bg-background [&_thead]:z-10'
        )}
        style={maxHeight ? { maxHeight } : undefined}
      >
        <UITable>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                    className={cn(dense && 'py-2')}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={finalColumns.length}
                  className="h-24 text-center"
                >
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="text-muted-foreground">Loading...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                  onClick={() => onRowClick?.(row.original)}
                  className={cn(
                    onRowClick && 'cursor-pointer',
                    dense && '[&_td]:py-2',
                    rowClassName?.(row)
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={finalColumns.length}
                  className="h-24 text-center"
                >
                  <EmptyState
                    message={emptyMessage}
                    description={emptyDescription}
                    icon={emptyIcon}
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </UITable>
      </div>

      {/* Pagination */}
      {enablePagination && data.length > 0 && (
        <PaginationControls
          pageIndex={table.getState().pagination.pageIndex}
          pageCount={table.getPageCount()}
          pageSize={table.getState().pagination.pageSize}
          totalRows={table.getFilteredRowModel().rows.length}
          selectedCount={table.getFilteredSelectedRowModel().rows.length}
          pageSizes={pageSizes}
          canPreviousPage={table.getCanPreviousPage()}
          canNextPage={table.getCanNextPage()}
          onPageChange={(index) => table.setPageIndex(index)}
          onPageSizeChange={(size) => table.setPageSize(size)}
          onPreviousPage={() => table.previousPage()}
          onNextPage={() => table.nextPage()}
        />
      )}

      {/* Footer */}
      {footer}
    </div>
  )
}

// ============================================================================
// Exports
// ============================================================================

export { type ColumnDef } from '@tanstack/react-table'
