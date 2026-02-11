import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Upload,
  FileUp,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  ArrowRight,
  ArrowLeft,
  Settings2,
  Columns3,
  Eye,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import {
  importExportApi,
  type ImportPreviewResponse,
  type ImportResultResponse,
  type LdifImportResultResponse,
  type CsvImportConfig,
  type ColumnMapping,
  type FixedValue,
  type ObjectType,
  type CsvSeparator,
} from '@/lib/api/import-export'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ImportFormat = 'csv' | 'ldif'

type WizardStep =
  | 'upload'      // Step 1: upload file
  | 'configure'   // Step 2: object type, separator, template, fixed values (CSV only)
  | 'mapping'     // Step 3: column mapping (CSV only)
  | 'preview'     // Step 4: preview & validate
  | 'result'      // Step 5: import results

const STEP_LABELS: Record<WizardStep, string> = {
  upload: 'Upload',
  configure: 'Configure',
  mapping: 'Column Mapping',
  preview: 'Preview',
  result: 'Results',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ImportPage() {
  // Wizard state
  const [step, setStep] = useState<WizardStep>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [importFormat, setImportFormat] = useState<ImportFormat>('csv')

  // CSV config state
  const [objectType, setObjectType] = useState<ObjectType>('user')
  const [separator, setSeparator] = useState<CsvSeparator>(',')
  const [templateId, setTemplateId] = useState<string>('')
  const [defaultPassword, setDefaultPassword] = useState('')
  const [departmentDn, setDepartmentDn] = useState('')
  const [fixedValues, setFixedValues] = useState<FixedValue[]>([])
  const [columnMappings, setColumnMappings] = useState<ColumnMapping[]>([])
  const [customObjectClasses, setCustomObjectClasses] = useState('')
  const [customRdnAttribute, setCustomRdnAttribute] = useState('cn')

  // LDIF config state
  const [overwrite, setOverwrite] = useState(false)

  // Preview / result state
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null)
  const [csvResult, setCsvResult] = useState<ImportResultResponse | null>(null)
  const [ldifResult, setLdifResult] = useState<LdifImportResultResponse | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // ---- Metadata queries ----

  const fieldsQuery = useQuery({
    queryKey: ['import-fields', objectType],
    queryFn: () => importExportApi.getAvailableFields(objectType),
    enabled: (step === 'configure' || step === 'mapping') && objectType !== 'custom',
  })

  const templatesQuery = useQuery({
    queryKey: ['import-templates', departmentDn],
    queryFn: () => importExportApi.getTemplates(departmentDn || undefined),
    enabled: step === 'configure',
  })

  // ---- Mutations ----

  const previewMutation = useMutation({
    mutationFn: () =>
      importExportApi.previewImport(file!, separator, objectType),
    onSuccess: (data) => {
      setPreview(data)
      // Auto-generate column mappings if not set
      if (columnMappings.length === 0 && data.headers.length > 0) {
        const allFields = fieldsQuery.data?.all_fields ?? []
        setColumnMappings(
          data.headers.map((h) => ({
            csv_column: h,
            ldap_attribute: allFields.includes(h) ? h : '',
          })),
        )
      }
    },
    onError: (err: Error) => {
      toast.error('Preview failed', { description: err.message })
    },
  })

  const csvImportMutation = useMutation({
    mutationFn: () => {
      const config: CsvImportConfig = {
        object_type: objectType,
        separator,
        template_id: templateId || undefined,
        column_mapping: columnMappings.filter((m) => m.ldap_attribute),
        fixed_values: fixedValues.filter((fv) => fv.attribute && fv.value),
        default_password: defaultPassword || undefined,
        department_dn: departmentDn || undefined,
        ...(objectType === 'custom' && {
          object_classes: customObjectClasses.split(',').map((s) => s.trim()).filter(Boolean),
          rdn_attribute: customRdnAttribute || undefined,
        }),
      }
      return importExportApi.importCsv(file!, config)
    },
    onSuccess: (data) => {
      setCsvResult(data)
      setStep('result')
      toast.success('CSV Import complete', {
        description: `${data.created} created, ${data.skipped} skipped`,
      })
    },
    onError: (err: Error) => {
      toast.error('CSV import failed', { description: err.message })
    },
  })

  const ldifImportMutation = useMutation({
    mutationFn: () => importExportApi.importLdif(file!, overwrite),
    onSuccess: (data) => {
      setLdifResult(data)
      setStep('result')
      toast.success('LDIF Import complete', {
        description: `${data.created} created, ${data.updated} updated, ${data.skipped} skipped`,
      })
    },
    onError: (err: Error) => {
      toast.error('LDIF import failed', { description: err.message })
    },
  })

  // ---- Handlers ----

  const detectFormat = (filename: string): ImportFormat => {
    const lower = filename.toLowerCase()
    if (lower.endsWith('.ldif') || lower.endsWith('.ldf')) return 'ldif'
    return 'csv'
  }

  const handleFileSelect = useCallback((f: File) => {
    const fmt = detectFormat(f.name)
    setFile(f)
    setImportFormat(fmt)
    if (fmt === 'ldif') {
      // LDIF goes straight to config (just overwrite toggle)
      setStep('configure')
    } else {
      setStep('configure')
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const f = e.dataTransfer.files[0]
      if (!f) return
      const ext = f.name.toLowerCase()
      if (ext.endsWith('.csv') || ext.endsWith('.ldif') || ext.endsWith('.ldf')) {
        handleFileSelect(f)
      } else {
        toast.error('Only CSV and LDIF files are supported')
      }
    },
    [handleFileSelect],
  )

  const handleNextFromConfigure = () => {
    if (importFormat === 'ldif') {
      // LDIF: go directly to import
      ldifImportMutation.mutate()
    } else {
      // CSV: preview first, then mapping
      previewMutation.mutate()
      setStep('mapping')
    }
  }

  const handleNextFromMapping = () => {
    setStep('preview')
  }

  const handleImport = () => {
    csvImportMutation.mutate()
  }

  const addFixedValue = () => {
    setFixedValues((prev) => [...prev, { attribute: '', value: '' }])
  }

  const removeFixedValue = (idx: number) => {
    setFixedValues((prev) => prev.filter((_, i) => i !== idx))
  }

  const updateFixedValue = (idx: number, field: 'attribute' | 'value', val: string) => {
    setFixedValues((prev) =>
      prev.map((fv, i) => (i === idx ? { ...fv, [field]: val } : fv)),
    )
  }

  const updateColumnMapping = (idx: number, ldapAttr: string) => {
    setColumnMappings((prev) =>
      prev.map((m, i) => (i === idx ? { ...m, ldap_attribute: ldapAttr } : m)),
    )
  }

  const reset = () => {
    setStep('upload')
    setFile(null)
    setImportFormat('csv')
    setObjectType('user')
    setSeparator(',')
    setTemplateId('')
    setDefaultPassword('')
    setDepartmentDn('')
    setFixedValues([])
    setColumnMappings([])
    setOverwrite(false)
    setPreview(null)
    setCsvResult(null)
    setLdifResult(null)
  }

  // Computed
  const csvSteps: WizardStep[] = ['upload', 'configure', 'mapping', 'preview', 'result']
  const ldifSteps: WizardStep[] = ['upload', 'configure', 'result']
  const steps = importFormat === 'ldif' ? ldifSteps : csvSteps
  const currentStepIdx = steps.indexOf(step)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Import</h1>
        <p className="text-muted-foreground">
          Import users or groups from CSV or LDIF files.
        </p>
      </div>

      {/* Step indicator */}
      {step !== 'upload' && (
        <div className="flex items-center gap-2 text-sm">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              {i > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
              <span
                className={
                  s === step
                    ? 'font-semibold text-primary'
                    : i < currentStepIdx
                      ? 'text-green-600'
                      : 'text-muted-foreground'
                }
              >
                {i < currentStepIdx && <CheckCircle className="inline h-3 w-3 mr-1" />}
                {STEP_LABELS[s]}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ================================================================ */}
      {/* STEP 1: Upload */}
      {/* ================================================================ */}
      {step === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload File</CardTitle>
            <CardDescription>
              Upload a CSV file (users, groups) or an LDIF file (any LDAP entries).
              The format is auto-detected from the file extension.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <FileUp className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium mb-2">
                Drag & drop a file here
              </p>
              <p className="text-sm text-muted-foreground mb-4">
                Supports <strong>.csv</strong>, <strong>.ldif</strong>, and <strong>.ldf</strong> files
              </p>
              <Input
                type="file"
                accept=".csv,.ldif,.ldf"
                className="max-w-xs mx-auto"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) handleFileSelect(f)
                }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================ */}
      {/* STEP 2: Configure */}
      {/* ================================================================ */}
      {step === 'configure' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-5 w-5" />
              Import Configuration
            </CardTitle>
            <CardDescription>
              {importFormat === 'csv'
                ? 'Configure how the CSV file should be parsed and imported.'
                : 'Configure LDIF import options.'}
              {' '}File: <strong>{file?.name}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {importFormat === 'csv' ? (
              <>
                {/* Object type & Separator */}
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Object Type</Label>
                    <Select
                      value={objectType}
                      onValueChange={(v) => setObjectType(v as ObjectType)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">Users (inetOrgPerson)</SelectItem>
                        <SelectItem value="group">Groups (groupOfNames)</SelectItem>
                        <SelectItem value="custom">Custom Object</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>CSV Separator</Label>
                    <Select
                      value={separator}
                      onValueChange={(v) => setSeparator(v as CsvSeparator)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value=",">Comma (,)</SelectItem>
                        <SelectItem value=";">Semicolon (;)</SelectItem>
                        <SelectItem value={'\t'}>Tab</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Template (optional)</Label>
                    <Select
                      value={templateId || '_none'}
                      onValueChange={(v) => setTemplateId(v === '_none' ? '' : v)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="No template" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_none">No template</SelectItem>
                        {templatesQuery.data?.templates.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Custom Object Type fields */}
                {objectType === 'custom' && (
                  <div className="rounded-lg border p-4 space-y-4 bg-muted/30">
                    <p className="text-sm font-medium">Custom Object Configuration</p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="objclasses">Object Classes (comma-separated)</Label>
                        <Input
                          id="objclasses"
                          value={customObjectClasses}
                          onChange={(e) => setCustomObjectClasses(e.target.value)}
                          placeholder="e.g., organizationalUnit, top"
                        />
                        <p className="text-xs text-muted-foreground">
                          LDAP objectClass values for the new entries
                        </p>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="rdnattr">RDN Attribute</Label>
                        <Input
                          id="rdnattr"
                          value={customRdnAttribute}
                          onChange={(e) => setCustomRdnAttribute(e.target.value)}
                          placeholder="e.g., cn, ou, uid"
                        />
                        <p className="text-xs text-muted-foreground">
                          Attribute used for the DN (e.g., cn=value,base_dn)
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Department DN & Default Password */}
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="dept">Target Department DN (optional)</Label>
                    <Input
                      id="dept"
                      value={departmentDn}
                      onChange={(e) => setDepartmentDn(e.target.value)}
                      placeholder="e.g., ou=engineering,dc=heracles,dc=local"
                    />
                  </div>
                  {(objectType === 'user' || objectType === 'custom') && (
                    <div className="space-y-2">
                      <Label htmlFor="pwd">Default Password (optional)</Label>
                      <Input
                        id="pwd"
                        type="password"
                        value={defaultPassword}
                        onChange={(e) => setDefaultPassword(e.target.value)}
                        placeholder="Password for all new users"
                      />
                    </div>
                  )}
                </div>

                {/* Fixed Values */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-base">Fixed Values</Label>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Constant values applied to every imported entry (overrides CSV data).
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={addFixedValue}>
                      <Plus className="h-3 w-3 mr-1" /> Add
                    </Button>
                  </div>
                  {fixedValues.map((fv, idx) => (
                    <div key={idx} className="flex gap-2 items-end">
                      <div className="flex-1">
                        <Label className="text-xs">Attribute</Label>
                        <Select
                          value={fv.attribute || '_none'}
                          onValueChange={(v) =>
                            updateFixedValue(idx, 'attribute', v === '_none' ? '' : v)
                          }
                        >
                          <SelectTrigger className="h-8">
                            <SelectValue placeholder="Select attribute" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="_none">—</SelectItem>
                            {fieldsQuery.data?.all_fields.map((f) => (
                              <SelectItem key={f} value={f}>
                                {f}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex-1">
                        <Label className="text-xs">Value</Label>
                        <Input
                          className="h-8"
                          value={fv.value}
                          onChange={(e) => updateFixedValue(idx, 'value', e.target.value)}
                          placeholder="Fixed value"
                        />
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive"
                        onClick={() => removeFixedValue(idx)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              /* LDIF config */
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Checkbox
                    id="overwrite"
                    checked={overwrite}
                    onCheckedChange={(v) => setOverwrite(v === true)}
                  />
                  <div>
                    <Label htmlFor="overwrite" className="cursor-pointer">
                      Overwrite existing entries
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      If enabled, entries that already exist in LDAP will be updated.
                      Otherwise, they are skipped.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <Separator />
            <div className="flex gap-3">
              <Button variant="outline" onClick={reset}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button
                onClick={handleNextFromConfigure}
                disabled={
                  previewMutation.isPending || ldifImportMutation.isPending
                }
              >
                {importFormat === 'ldif' ? (
                  ldifImportMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Importing...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" /> Import LDIF
                    </>
                  )
                ) : previewMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Parsing...
                  </>
                ) : (
                  <>
                    Next: Column Mapping <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================ */}
      {/* STEP 3: Column Mapping (CSV only) */}
      {/* ================================================================ */}
      {step === 'mapping' && preview && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Columns3 className="h-5 w-5" />
              Column Mapping
            </CardTitle>
            <CardDescription>
              Map each CSV column to an LDAP attribute. Unmatched columns will be
              skipped. Required fields for {objectType}s:{' '}
              <strong>
                {fieldsQuery.data?.required_fields.join(', ') || 'loading...'}
              </strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/3">CSV Column</TableHead>
                    <TableHead>→</TableHead>
                    <TableHead className="w-1/3">LDAP Attribute</TableHead>
                    <TableHead className="w-1/4">Sample Value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {columnMappings.map((m, idx) => (
                    <TableRow key={m.csv_column}>
                      <TableCell className="font-mono text-sm">
                        {m.csv_column}
                      </TableCell>
                      <TableCell>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </TableCell>
                      <TableCell>
                        <Select
                          value={m.ldap_attribute || '_skip'}
                          onValueChange={(v) =>
                            updateColumnMapping(idx, v === '_skip' ? '' : v)
                          }
                        >
                          <SelectTrigger className="h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="_skip">
                              <span className="text-muted-foreground">— Skip —</span>
                            </SelectItem>
                            {fieldsQuery.data?.all_fields.map((f) => (
                              <SelectItem key={f} value={f}>
                                {f}
                                {fieldsQuery.data?.required_fields.includes(f) && ' *'}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {preview.rows[0]?.attributes[m.csv_column] || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <Separator />
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep('configure')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button onClick={handleNextFromMapping}>
                Next: Preview <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================ */}
      {/* STEP 4: Preview (CSV) */}
      {/* ================================================================ */}
      {step === 'preview' && preview && (
        <>
          {/* Stats cards */}
          <div className="flex gap-4">
            <Card className="flex-1">
              <CardContent className="pt-6 text-center">
                <p className="text-3xl font-bold">{preview.total_rows}</p>
                <p className="text-sm text-muted-foreground">Total Rows</p>
              </CardContent>
            </Card>
            <Card className="flex-1">
              <CardContent className="pt-6 text-center">
                <p className="text-3xl font-bold text-green-600">
                  {preview.valid_rows}
                </p>
                <p className="text-sm text-muted-foreground">Valid</p>
              </CardContent>
            </Card>
            <Card className="flex-1">
              <CardContent className="pt-6 text-center">
                <p className="text-3xl font-bold text-red-600">
                  {preview.invalid_rows}
                </p>
                <p className="text-sm text-muted-foreground">Invalid</p>
              </CardContent>
            </Card>
          </div>

          {/* Config summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Import Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 text-sm md:grid-cols-3">
                <div>
                  <span className="text-muted-foreground">Object type:</span>{' '}
                  <strong>{objectType}</strong>
                </div>
                <div>
                  <span className="text-muted-foreground">Separator:</span>{' '}
                  <strong>
                    {separator === ',' ? 'Comma' : separator === ';' ? 'Semicolon' : 'Tab'}
                  </strong>
                </div>
                {templateId && (
                  <div>
                    <span className="text-muted-foreground">Template:</span>{' '}
                    <strong>
                      {templatesQuery.data?.templates.find((t) => t.id === templateId)
                        ?.name || templateId}
                    </strong>
                  </div>
                )}
                {departmentDn && (
                  <div>
                    <span className="text-muted-foreground">Department:</span>{' '}
                    <strong className="font-mono text-xs">{departmentDn}</strong>
                  </div>
                )}
                {fixedValues.filter((fv) => fv.attribute).length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Fixed values:</span>{' '}
                    <strong>
                      {fixedValues
                        .filter((fv) => fv.attribute)
                        .map((fv) => `${fv.attribute}=${fv.value}`)
                        .join(', ')}
                    </strong>
                  </div>
                )}
                {columnMappings.filter((m) => m.ldap_attribute && m.csv_column !== m.ldap_attribute).length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Remapped columns:</span>{' '}
                    <strong>
                      {columnMappings
                        .filter(
                          (m) =>
                            m.ldap_attribute &&
                            m.csv_column !== m.ldap_attribute,
                        )
                        .map((m) => `${m.csv_column}→${m.ldap_attribute}`)
                        .join(', ')}
                    </strong>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Preview table */}
          <Card>
            <CardHeader>
              <CardTitle>Data Preview: {file?.name}</CardTitle>
              <CardDescription>
                Showing first {preview.rows.length} of {preview.total_rows} rows.
                Columns: {preview.headers.join(', ')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border overflow-auto max-h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Row</TableHead>
                      <TableHead className="w-16">Status</TableHead>
                      {preview.headers.map((h) => (
                        <TableHead key={h}>{h}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.rows.map((row) => (
                      <TableRow
                        key={row.row}
                        className={row.valid ? '' : 'bg-red-50 dark:bg-red-950/30'}
                      >
                        <TableCell className="font-mono text-xs">{row.row}</TableCell>
                        <TableCell>
                          {row.valid ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                        </TableCell>
                        {preview.headers.map((h) => (
                          <TableCell key={h} className="text-sm">
                            {row.attributes[h] || ''}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setStep('mapping')}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            <Button
              onClick={handleImport}
              disabled={csvImportMutation.isPending || preview.valid_rows === 0}
            >
              {csvImportMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Importing...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Import {preview.valid_rows} {objectType === 'user' ? 'Users' : 'Groups'}
                </>
              )}
            </Button>
          </div>
        </>
      )}

      {/* ================================================================ */}
      {/* STEP 5: Results */}
      {/* ================================================================ */}
      {step === 'result' && (csvResult || ldifResult) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {(csvResult?.errors.length === 0 && ldifResult?.errors.length === 0) ||
              (!csvResult?.errors.length && !ldifResult?.errors.length) ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              )}
              Import Complete
            </CardTitle>
            <CardDescription>
              {importFormat === 'csv' ? 'CSV' : 'LDIF'} import finished.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Stats badges */}
            <div className="flex gap-4 flex-wrap">
              {csvResult && (
                <>
                  <Badge variant="default" className="text-sm py-1 px-3">
                    {csvResult.created} Created
                  </Badge>
                  {csvResult.updated > 0 && (
                    <Badge className="text-sm py-1 px-3 bg-blue-600">
                      {csvResult.updated} Updated
                    </Badge>
                  )}
                  {csvResult.skipped > 0 && (
                    <Badge variant="secondary" className="text-sm py-1 px-3">
                      {csvResult.skipped} Skipped
                    </Badge>
                  )}
                  {csvResult.errors.length > 0 && (
                    <Badge variant="destructive" className="text-sm py-1 px-3">
                      {csvResult.errors.length} Errors
                    </Badge>
                  )}
                </>
              )}
              {ldifResult && (
                <>
                  <Badge variant="default" className="text-sm py-1 px-3">
                    {ldifResult.created} Created
                  </Badge>
                  {ldifResult.updated > 0 && (
                    <Badge className="text-sm py-1 px-3 bg-blue-600">
                      {ldifResult.updated} Updated
                    </Badge>
                  )}
                  {ldifResult.skipped > 0 && (
                    <Badge variant="secondary" className="text-sm py-1 px-3">
                      {ldifResult.skipped} Skipped
                    </Badge>
                  )}
                  {ldifResult.errors.length > 0 && (
                    <Badge variant="destructive" className="text-sm py-1 px-3">
                      {ldifResult.errors.length} Errors
                    </Badge>
                  )}
                </>
              )}
            </div>

            {/* Error table */}
            {((csvResult?.errors.length ?? 0) > 0 ||
              (ldifResult?.errors.length ?? 0) > 0) && (
              <div className="rounded-md border overflow-auto max-h-[300px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entry</TableHead>
                      <TableHead>Field</TableHead>
                      <TableHead>Error</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(csvResult?.errors || ldifResult?.errors || []).map(
                      (err, i) => (
                        <TableRow key={i}>
                          <TableCell>{err.row}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {err.field}
                          </TableCell>
                          <TableCell className="text-sm">{err.message}</TableCell>
                        </TableRow>
                      ),
                    )}
                  </TableBody>
                </Table>
              </div>
            )}

            <Button onClick={reset}>
              <FileText className="mr-2 h-4 w-4" />
              Import Another File
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export { ImportPage as default }
