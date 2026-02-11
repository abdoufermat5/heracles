import { useState, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  FileDown,
  FileSpreadsheet,
  Database,
  Loader2,
  Users,
  FolderTree,
  Globe,
  Filter,
  Plug,
  Info,
  Check,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { toast } from 'sonner'
import { PageHeader } from '@/components/common/page-header'
import { cn } from '@/lib/utils'
import {
  importExportApi,
  type ExportRequest,
  type ExportFormat,
  type ObjectType,
} from '@/lib/api/import-export'

// ---------------------------------------------------------------------------
// Format & object type option definitions
// ---------------------------------------------------------------------------

const FORMAT_OPTIONS: {
  value: ExportFormat
  label: string
  description: string
  icon: React.ElementType
}[] = [
  {
    value: 'csv',
    label: 'CSV',
    description: 'Spreadsheet-friendly format for Excel, Google Sheets, or re-import',
    icon: FileSpreadsheet,
  },
  {
    value: 'ldif',
    label: 'LDIF',
    description: 'Standard LDAP interchange format (RFC 2849) for ldapadd / ldapmodify',
    icon: Database,
  },
]

const OBJECT_TYPE_OPTIONS: {
  value: ObjectType | 'raw'
  label: string
  icon: React.ElementType
}[] = [
  { value: 'user', label: 'Users', icon: Users },
  { value: 'group', label: 'Groups', icon: FolderTree },
  { value: 'raw', label: 'Any LDAP Object', icon: Globe },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExportPage() {
  const [format, setFormat] = useState<ExportFormat>('csv')
  const [objectType, setObjectType] = useState<ObjectType | 'raw'>('user')
  const [filter, setFilter] = useState('')
  const [departmentDn, setDepartmentDn] = useState('')
  const [ldifWrap, setLdifWrap] = useState(76)
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set())
  const [selectAll, setSelectAll] = useState(true)
  const [showFilters, setShowFilters] = useState(false)

  const isRawMode = objectType === 'raw'

  // Fetch available fields for the selected object type (skip for raw mode)
  const fieldsQuery = useQuery({
    queryKey: ['export-fields', objectType],
    queryFn: () => importExportApi.getAvailableFields(objectType as ObjectType),
    enabled: !isRawMode,
  })

  const exportMutation = useMutation({
    mutationFn: (req: ExportRequest) => importExportApi.exportEntries(req),
    onSuccess: (data) => {
      const ext = format === 'csv' ? 'csv' : 'ldif'
      const mime = format === 'csv' ? 'text/csv' : 'application/ldif'
      const typeLabel = isRawMode ? 'entries' : objectType === 'user' ? 'users' : 'groups'
      const blob = new Blob([data], { type: mime })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `heracles-${typeLabel}-${new Date().toISOString().slice(0, 10)}.${ext}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Export downloaded')
    },
    onError: (err: Error) => {
      toast.error('Export failed', { description: err.message })
    },
  })

  const toggleField = (field: string) => {
    setSelectAll(false)
    setSelectedFields((prev) => {
      const next = new Set(prev)
      if (next.has(field)) {
        next.delete(field)
      } else {
        next.add(field)
      }
      return next
    })
  }

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectAll(false)
      setSelectedFields(new Set())
    } else {
      setSelectAll(true)
      setSelectedFields(new Set())
    }
  }

  const handleExport = () => {
    const fields =
      selectAll || isRawMode
        ? undefined
        : selectedFields.size > 0
          ? Array.from(selectedFields)
          : undefined

    exportMutation.mutate({
      format,
      object_type: isRawMode ? null : (objectType as ObjectType),
      fields,
      department_dn: departmentDn || undefined,
      filter: filter || undefined,
      ldif_wrap: ldifWrap,
    })
  }

  const requiredFields = fieldsQuery.data?.required_fields ?? []
  const optionalFields = fieldsQuery.data?.optional_fields ?? []
  const pluginFieldGroups = fieldsQuery.data?.plugin_fields ?? []

  // Summary counts
  const totalFieldCount = useMemo(() => {
    const pluginCount = pluginFieldGroups.reduce((acc, g) => acc + g.fields.length, 0)
    return requiredFields.length + optionalFields.length + pluginCount
  }, [requiredFields, optionalFields, pluginFieldGroups])

  const selectedCount = selectAll ? totalFieldCount : selectedFields.size
  const hasActiveFilters = !!departmentDn || !!filter

  const typeLabel = isRawMode
    ? 'Entries'
    : objectType === 'user'
      ? 'Users'
      : 'Groups'

  return (
    <div className="space-y-6">
      <PageHeader
        title="Export"
        description="Export directory entries as CSV or LDIF files."
      />

      {/* ------------------------------------------------------------------ */}
      {/* 1. Format Selection                                                 */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Format</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {FORMAT_OPTIONS.map((opt) => {
              const Icon = opt.icon
              const selected = format === opt.value
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFormat(opt.value)}
                  className={cn(
                    'relative flex items-start gap-4 rounded-lg border-2 p-4 text-left transition-all',
                    'hover:border-primary/50 hover:bg-accent/50',
                    selected
                      ? 'border-primary bg-primary/5'
                      : 'border-muted',
                  )}
                >
                  <div
                    className={cn(
                      'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                      selected
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground',
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{opt.label}</span>
                      {selected && (
                        <Check className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {opt.description}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>

          {/* LDIF-specific option */}
          {format === 'ldif' && (
            <div className="mt-4 flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
              <Label htmlFor="wrap" className="whitespace-nowrap text-sm">
                Line wrap
              </Label>
              <Input
                id="wrap"
                type="number"
                min={0}
                max={1000}
                value={ldifWrap}
                onChange={(e) => setLdifWrap(Number(e.target.value))}
                className="w-24"
              />
              <span className="text-xs text-muted-foreground">
                characters (0 = no wrapping, 76 = RFC default)
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 2. Object Type                                                      */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">What to Export</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {OBJECT_TYPE_OPTIONS.map((opt) => {
              const Icon = opt.icon
              const selected = objectType === opt.value
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    setObjectType(opt.value)
                    setSelectAll(true)
                    setSelectedFields(new Set())
                  }}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all',
                    'hover:border-primary/50 hover:bg-accent/50',
                    selected
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-muted bg-background text-muted-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {opt.label}
                </button>
              )
            })}
          </div>

          {/* Advanced filters toggle */}
          <div>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Filter className="h-3.5 w-3.5" />
              Advanced filters
              {hasActiveFilters && (
                <Badge variant="secondary" className="ml-1 text-[10px] px-1.5 py-0">
                  active
                </Badge>
              )}
            </button>

            {showFilters && (
              <div className="mt-3 grid gap-3 sm:grid-cols-2 rounded-lg border bg-muted/20 p-4">
                <div className="space-y-1.5">
                  <Label htmlFor="department" className="text-xs">
                    Search Base DN
                  </Label>
                  <Input
                    id="department"
                    value={departmentDn}
                    onChange={(e) => setDepartmentDn(e.target.value)}
                    placeholder={
                      isRawMode
                        ? 'dc=heracles,dc=local'
                        : objectType === 'user'
                          ? 'ou=people,dc=heracles,dc=local'
                          : 'ou=groups,dc=heracles,dc=local'
                    }
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="filter" className="text-xs">
                    LDAP Filter
                  </Label>
                  <Input
                    id="filter"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder={
                      isRawMode
                        ? '(objectClass=organizationalUnit)'
                        : objectType === 'user'
                          ? '(title=Engineer)'
                          : '(cn=admin*)'
                    }
                    className="h-9 text-sm"
                  />
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 3. Field Selection                                                  */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Fields</CardTitle>
            {!isRawMode && (
              <button
                type="button"
                onClick={handleSelectAll}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all',
                  selectAll
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-muted hover:border-primary/50',
                )}
              >
                {selectAll && <Check className="h-3 w-3" />}
                All fields
                {!isRawMode && (
                  <span className="opacity-70">({totalFieldCount})</span>
                )}
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isRawMode ? (
            <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-4">
              <Info className="h-5 w-5 shrink-0 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm font-medium">Raw LDAP mode</p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  All attributes found on matching entries will be exported.
                  Use the advanced filters above to control which entries are included.
                </p>
              </div>
            </div>
          ) : fieldsQuery.isLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading available fields...
            </div>
          ) : (
            <Accordion
              type="multiple"
              defaultValue={['required', 'optional', ...pluginFieldGroups.map((g) => g.plugin_name)]}
              className="space-y-1"
            >
              {/* Required fields */}
              {requiredFields.length > 0 && (
                <AccordionItem value="required" className="border rounded-lg px-1">
                  <AccordionTrigger className="py-3 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Required</span>
                      <Badge variant="secondary" className="text-[10px]">
                        {requiredFields.length}
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="flex flex-wrap gap-2 pb-1">
                      {requiredFields.map((f) => (
                        <FieldChip
                          key={f}
                          name={f}
                          checked={selectAll || selectedFields.has(f)}
                          disabled={selectAll}
                          onToggle={() => toggleField(f)}
                        />
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Optional fields */}
              {optionalFields.length > 0 && (
                <AccordionItem value="optional" className="border rounded-lg px-1">
                  <AccordionTrigger className="py-3 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Optional</span>
                      <Badge variant="outline" className="text-[10px]">
                        {optionalFields.length}
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="flex flex-wrap gap-2 pb-1">
                      {optionalFields.map((f) => (
                        <FieldChip
                          key={f}
                          name={f}
                          checked={selectAll || selectedFields.has(f)}
                          disabled={selectAll}
                          onToggle={() => toggleField(f)}
                        />
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}

              {/* Plugin field groups */}
              {pluginFieldGroups.map((group) => (
                <AccordionItem
                  key={group.plugin_name}
                  value={group.plugin_name}
                  className="border rounded-lg px-1"
                >
                  <AccordionTrigger className="py-3 hover:no-underline">
                    <div className="flex items-center gap-2">
                      <Plug className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium">
                        {group.plugin_label}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {group.fields.length}
                      </Badge>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="flex flex-wrap gap-2 pb-1">
                      {group.fields.map((f) => (
                        <FieldChip
                          key={f.name}
                          name={f.name}
                          label={f.label}
                          description={f.description || undefined}
                          checked={selectAll || selectedFields.has(f.name)}
                          disabled={selectAll}
                          onToggle={() => toggleField(f.name)}
                        />
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}

          {format === 'ldif' && !isRawMode && (
            <p className="mt-3 text-xs text-muted-foreground">
              <code className="rounded bg-muted px-1 py-0.5">objectClass</code>{' '}
              is always included in LDIF exports.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 4. Export Action                                                     */}
      {/* ------------------------------------------------------------------ */}
      <Card className="border-primary/20 bg-primary/[0.02]">
        <CardContent className="flex flex-col items-center gap-4 py-6 sm:flex-row sm:justify-between">
          <div className="text-center sm:text-left">
            <p className="text-sm font-medium">
              Ready to export{' '}
              <span className="text-primary">{typeLabel.toLowerCase()}</span>{' '}
              as{' '}
              <span className="text-primary">{format.toUpperCase()}</span>
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {isRawMode
                ? 'All attributes'
                : selectAll
                  ? `All ${totalFieldCount} fields selected`
                  : `${selectedCount} of ${totalFieldCount} fields selected`}
              {hasActiveFilters && ' · Custom filters applied'}
            </p>
          </div>
          <Button
            onClick={handleExport}
            disabled={exportMutation.isPending || (!isRawMode && !selectAll && selectedCount === 0)}
            size="lg"
            className="min-w-[200px]"
          >
            {exportMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <FileDown className="mr-2 h-5 w-5" />
                Export {typeLabel}
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// FieldChip — compact toggleable field badge
// ---------------------------------------------------------------------------

function FieldChip({
  name,
  label,
  description,
  checked,
  disabled,
  onToggle,
}: {
  name: string
  label?: string
  description?: string
  checked: boolean
  disabled: boolean
  onToggle: () => void
}) {
  return (
    <div
      role="checkbox"
      aria-checked={checked}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onToggle()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === ' ' || e.key === 'Enter')) {
          e.preventDefault()
          onToggle()
        }
      }}
      title={description}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-all select-none',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        disabled && 'opacity-60 cursor-default',
        !disabled && 'cursor-pointer hover:border-primary/50',
        checked
          ? 'border-primary/40 bg-primary/10 text-foreground'
          : 'border-muted bg-background text-muted-foreground',
      )}
    >
      <Checkbox
        checked={checked}
        className="h-3.5 w-3.5 pointer-events-none"
        tabIndex={-1}
      />
      <span className="font-mono">{name}</span>
      {label && (
        <span className="text-muted-foreground font-sans hidden sm:inline">
          {label}
        </span>
      )}
    </div>
  )
}

export { ExportPage as default }
