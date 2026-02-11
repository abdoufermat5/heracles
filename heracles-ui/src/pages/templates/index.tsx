import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  FileText,
  Plus,
  Trash2,
  Pencil,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Form } from '@/components/ui/form'
import { toast } from 'sonner'
import { FormInput, FormTextarea } from '@/components/common'
import { templatesApi, type TemplateCreate, type TemplateResponse } from '@/lib/api/templates'
import { templateCreateSchema, type TemplateCreateFormData } from '@/lib/schemas'
import { ROUTES } from '@/config/constants'

export function TemplatesListPage() {

  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const form = useForm<TemplateCreateFormData>({
    resolver: zodResolver(templateCreateSchema),
    defaultValues: {
      name: '',
      description: '',
      defaults: '{\n  "objectClasses": ["inetOrgPerson"],\n  "loginShell": "/bin/bash",\n  "homeDirectory": "/home/{{uid}}"\n}',
    },
  })

  const { data, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templatesApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: (data: TemplateCreate) => templatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setCreateOpen(false)
      form.reset()
      toast.success('Template created')
    },
    onError: (err: Error) => {
      toast.error('Failed to create template', { description: err.message })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => templatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setDeleteId(null)
      toast.success('Template deleted')
    },
  })

  const handleCreate = (data: TemplateCreateFormData) => {
    try {
      const defaults = JSON.parse(data.defaults)
      createMutation.mutate({ name: data.name, description: data.description || undefined, defaults })
    } catch {
      toast.error('Invalid JSON in defaults')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">User Templates</h1>
          <p className="text-muted-foreground">
            Reusable templates for bulk user creation with variable placeholders.
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Template
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Template</DialogTitle>
              <DialogDescription>
                Define a reusable template with default values and variable placeholders like {'{{uid}}'}.
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleCreate)} className="space-y-4 py-4">
                <FormInput control={form.control} name="name" label="Name" placeholder="e.g., Standard Employee" />
                <FormInput control={form.control} name="description" label="Description" placeholder="Optional description" />
                <FormTextarea
                  control={form.control}
                  name="defaults"
                  label="Default Values (JSON)"
                  rows={8}
                  className="font-mono text-sm"
                />
                <DialogFooter>
                  <Button variant="outline" type="button" onClick={() => setCreateOpen(false)}>Cancel</Button>
                  <Button type="submit" disabled={createMutation.isPending}>
                    Create
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading templates...</div>
      ) : !data?.templates.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No templates yet. Create your first template to streamline user creation.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.templates.map((tmpl: TemplateResponse) => (
            <Card key={tmpl.id} className="relative group">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{tmpl.name}</CardTitle>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                      <Link to={`${ROUTES.TEMPLATES}/${tmpl.id}`}>
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => setDeleteId(tmpl.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {tmpl.description && (
                  <CardDescription>{tmpl.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Object.keys(tmpl.defaults).slice(0, 5).map((key) => (
                    <Badge key={key} variant="secondary" className="text-xs">
                      {key}
                    </Badge>
                  ))}
                  {Object.keys(tmpl.defaults).length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{Object.keys(tmpl.defaults).length - 5} more
                    </Badge>
                  )}
                </div>
                {tmpl.department_dn && (
                  <p className="text-xs text-muted-foreground truncate">
                    Scope: {tmpl.department_dn.split(',')[0]}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  Created {new Date(tmpl.created_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Template</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this template? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              disabled={deleteMutation.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export { TemplatesListPage as default }
