import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft, Save, Eye, Plug } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Form } from '@/components/ui/form'
import { toast } from 'sonner'
import { FormInput, FormTextarea } from '@/components/common'
import { templatesApi, type TemplateUpdate, type TemplatePreview } from '@/lib/api/templates'
import { templateUpdateSchema, type TemplateUpdateFormData } from '@/lib/schemas'
import { useTemplatePluginFields } from '@/hooks'
import { ROUTES } from '@/config/constants'

export function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState<TemplatePreview | null>(null)

  const form = useForm<TemplateUpdateFormData>({
    resolver: zodResolver(templateUpdateSchema),
    defaultValues: {
      name: '',
      description: '',
      defaults: '{}',
      variables: '',
      departmentDn: '',
      displayOrder: 0,
    },
  })

  // Fetch available plugin fields for the template editor
  const { data: pluginFieldSections } = useTemplatePluginFields('user')

  const { data: template, isLoading, error } = useQuery({
    queryKey: ['template', id],
    queryFn: () => templatesApi.get(id!),
    enabled: !!id,
  })

  const initialPluginActivations = useMemo(
    () => template?.plugin_activations || {},
    [template?.plugin_activations]
  )
  const [pluginActivationOverrides, setPluginActivations] = useState<Record<string, Record<string, unknown>> | null>(null)
  const pluginActivations = pluginActivationOverrides ?? initialPluginActivations

  // Populate form when template loads
  useEffect(() => {
    if (template) {
      form.reset({
        name: template.name,
        description: template.description || '',
        defaults: JSON.stringify(template.defaults, null, 2),
        variables: template.variables ? JSON.stringify(template.variables, null, 2) : '',
        departmentDn: template.department_dn || '',
        displayOrder: template.display_order ?? 0,
      })
    }
  }, [template, form])

  const updateMutation = useMutation({
    mutationFn: (data: TemplateUpdate) => templatesApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template', id] })
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      toast.success('Template updated')
    },
    onError: (err: Error) => {
      toast.error('Failed to update template', { description: err.message })
    },
  })

  const previewMutation = useMutation({
    mutationFn: (values: Record<string, string>) =>
      templatesApi.preview(id!, values),
    onSuccess: (data) => {
      setPreviewData(data)
      setPreviewOpen(true)
    },
    onError: (err: Error) => {
      toast.error('Preview failed', { description: err.message })
    },
  })

  const handleSave = (data: TemplateUpdateFormData) => {
    let parsedDefaults: Record<string, unknown>
    try {
      parsedDefaults = JSON.parse(data.defaults)
    } catch {
      return // Zod should catch this, but just in case
    }

    let parsedVariables: Record<string, { default?: string; description?: string }> | undefined
    if (data.variables?.trim()) {
      try {
        parsedVariables = JSON.parse(data.variables)
      } catch {
        return
      }
    }

    const payload: TemplateUpdate = {
      name: data.name,
      description: data.description || undefined,
      defaults: parsedDefaults,
      pluginActivations: Object.keys(pluginActivations).length > 0 ? pluginActivations : undefined,
      variables: parsedVariables,
      departmentDn: data.departmentDn || undefined,
      displayOrder: data.displayOrder || undefined,
    }
    updateMutation.mutate(payload)
  }

  const handlePreview = () => {
    const defaultsStr = form.getValues('defaults')
    const placeholderPattern = /\{\{(\w+)\}\}/g
    const variableNames: string[] = []
    let match
    while ((match = placeholderPattern.exec(defaultsStr)) !== null) {
      if (!variableNames.includes(match[1])) {
        variableNames.push(match[1])
      }
    }

    // Build sample values
    const sampleValues: Record<string, string> = {}
    for (const v of variableNames) {
      sampleValues[v] = `sample_${v}`
    }
    previewMutation.mutate(sampleValues)
  }

  if (isLoading) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Loading template...
      </div>
    )
  }

  if (error || !template) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate(ROUTES.TEMPLATES)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Templates
        </Button>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Template not found.
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.TEMPLATES)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Edit Template</h1>
            <p className="text-muted-foreground">
              Modify template settings and default values.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePreview} disabled={previewMutation.isPending}>
            <Eye className="mr-2 h-4 w-4" />
            Preview
          </Button>
          <Button type="submit" form="template-form" disabled={updateMutation.isPending}>
            <Save className="mr-2 h-4 w-4" />
            {updateMutation.isPending ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      <Form {...form}>
        <form id="template-form" onSubmit={form.handleSubmit(handleSave)} className="grid gap-6 lg:grid-cols-2">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Template name and metadata</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormInput control={form.control} name="name" label="Name" placeholder="Template name" />
              <FormInput control={form.control} name="description" label="Description" placeholder="Optional description" />
              <FormInput
                control={form.control}
                name="departmentDn"
                label="Department DN (optional)"
                placeholder="ou=engineering,ou=departments,dc=example,dc=com"
                className="font-mono text-sm"
              />
              <FormInput control={form.control} name="displayOrder" label="Display Order" type="number" className="w-24" />
              <div className="text-xs text-muted-foreground space-y-1">
                <p>Created: {new Date(template.created_at).toLocaleString()}</p>
                <p>Updated: {new Date(template.updated_at).toLocaleString()}</p>
                {template.created_by && <p>By: {template.created_by}</p>}
              </div>
            </CardContent>
          </Card>

          {/* Variables */}
          <Card>
            <CardHeader>
              <CardTitle>Variable Definitions</CardTitle>
              <CardDescription>
                Define template variables with optional defaults and descriptions (JSON)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormTextarea
                control={form.control}
                name="variables"
                label=""
                rows={8}
                className="font-mono text-sm"
                placeholder={'{\n  "uid": { "description": "Username" },\n  "department": { "default": "Engineering" }\n}'}
              />
            </CardContent>
          </Card>

          {/* Plugin Activations */}
          {pluginFieldSections && Object.keys(pluginFieldSections).length > 0 && (
            <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plug className="h-5 w-5" />
                Plugin Activations
              </CardTitle>
              <CardDescription>
                Enable plugins that will be automatically activated when creating users from this template.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {Object.entries(pluginFieldSections).map(([pluginName, section]) => {
                const isActive = pluginName in pluginActivations
                const pluginConfig = (pluginActivations[pluginName] || {}) as Record<string, unknown>

                return (
                  <div key={pluginName} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm font-medium">{section.label}</Label>
                        {section.objectClasses?.length > 0 && (
                          <p className="text-xs text-muted-foreground">
                            Object classes: {section.objectClasses.join(', ')}
                          </p>
                        )}
                      </div>
                      <Switch
                        checked={isActive}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            // Activate with default values from field definitions
                            const defaults: Record<string, unknown> = {}
                            for (const field of section.fields) {
                              if (field.defaultValue != null) {
                                defaults[field.key] = field.defaultValue
                              }
                            }
                            setPluginActivations((prev) => ({ ...(prev ?? {}), [pluginName]: defaults }))
                          } else {
                            setPluginActivations((prev) => {
                              const next = { ...(prev ?? {}) }
                              delete next[pluginName]
                              return next
                            })
                          }
                        }}
                      />
                    </div>

                    {isActive && section.fields.length > 0 && (
                      <div className="ml-4 grid gap-3 md:grid-cols-2 border-l-2 border-muted pl-4">
                        {section.fields.map((field) => (
                          <div key={field.key} className="space-y-1">
                            <Label className="text-xs">{field.label}</Label>
                            <Input
                              value={String(pluginConfig[field.key] ?? field.defaultValue ?? '')}
                              onChange={(e) => {
                                const val = field.fieldType === 'integer'
                                  ? (e.target.value ? Number(e.target.value) : '')
                                  : e.target.value
                                setPluginActivations((prev) => ({
                                  ...(prev ?? {}),
                                  [pluginName]: {
                                    ...(prev ?? {})[pluginName],
                                    [field.key]: val,
                                  },
                                }))
                              }}
                              type={field.fieldType === 'integer' ? 'number' : 'text'}
                              placeholder={field.description || undefined}
                              className="h-8 text-sm"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </CardContent>
          </Card>
          )}

          {/* Defaults JSON */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Default Values (JSON)</CardTitle>
              <CardDescription>
                LDAP attributes to set when creating users from this template. Use {'{{variable}}'} for
                placeholders.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormTextarea
                control={form.control}
                name="defaults"
                label=""
                rows={12}
                className="font-mono text-sm"
              />
            </CardContent>
          </Card>
        </form>
      </Form>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Template Preview</DialogTitle>
          </DialogHeader>
          {previewData && (
            <div className="space-y-4">
              <div>
                <Label className="text-sm font-medium">Resolved Defaults</Label>
                <pre className="mt-2 rounded-md bg-muted p-4 text-sm font-mono overflow-auto max-h-64">
                  {JSON.stringify(previewData.resolved_defaults, null, 2)}
                </pre>
              </div>
              {previewData.missing_variables.length > 0 && (
                <div>
                  <Label className="text-sm font-medium">Missing Variables</Label>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {previewData.missing_variables.map((v) => (
                      <Badge key={v} variant="destructive">
                        {v}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export { TemplateDetailPage as default }
