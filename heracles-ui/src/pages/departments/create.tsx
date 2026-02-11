import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Form } from '@/components/ui/form'
import { PageHeader, LoadingSpinner, FormInput, FormTextarea, FormSelect } from '@/components/common'
import { useCreateDepartment, useDepartmentTree } from '@/hooks'
import { departmentCreateSchema, type DepartmentCreateFormData } from '@/lib/schemas'
import { ROUTES } from '@/config/routes'

export function DepartmentCreatePage() {
  const navigate = useNavigate()
  const createMutation = useCreateDepartment()
  const { data: treeData } = useDepartmentTree()

  const form = useForm<DepartmentCreateFormData>({
    resolver: zodResolver(departmentCreateSchema),
    defaultValues: {
      ou: '',
      description: '',
      parentDn: '',
      hrcDepartmentCategory: '',
      hrcDepartmentManager: '',
    },
  })

  // Flatten tree for parent selection
  const flattenDepartments = (
    nodes: NonNullable<typeof treeData>['tree'],
    result: { dn: string; path: string }[] = []
  ) => {
    for (const node of nodes || []) {
      result.push({ dn: node.dn, path: node.path })
      if (node.children) {
        flattenDepartments(node.children, result)
      }
    }
    return result
  }
  const parentOptions = flattenDepartments(treeData?.tree || [])

  const onSubmit = async (data: DepartmentCreateFormData) => {
    try {
      await createMutation.mutateAsync({
        ou: data.ou,
        description: data.description || undefined,
        parentDn: data.parentDn || undefined,
        hrcDepartmentCategory: data.hrcDepartmentCategory || undefined,
        hrcDepartmentManager: data.hrcDepartmentManager || undefined,
      })
      toast.success(`Department "${data.ou}" created successfully`)
      navigate(ROUTES.DEPARTMENTS)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to create department'
      )
    }
  }

  return (
    <div>
      <PageHeader
        title="Create Department"
        description="Add a new organizational unit to the directory"
        actions={
          <Button variant="outline" onClick={() => navigate(ROUTES.DEPARTMENTS)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        }
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Department Information
              </CardTitle>
              <CardDescription>
                Basic information about the department
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormInput
                control={form.control}
                name="ou"
                label="Name *"
                placeholder="Engineering"
                description="Unique identifier for the department"
              />

              <FormSelect
                control={form.control}
                name="parentDn"
                label="Parent Department"
                noneOption="Root (no parent)"
                options={parentOptions.map((opt) => ({
                  value: opt.dn,
                  label: opt.path,
                }))}
                placeholder="Root (no parent)"
                description="Optional parent department for hierarchy"
              />

              <FormTextarea
                control={form.control}
                name="description"
                label="Description"
                placeholder="Enter a description for this department..."
                className="md:col-span-2"
              />

              <FormSelect
                control={form.control}
                name="hrcDepartmentCategory"
                label="Category"
                noneOption="None"
                options={[
                  { value: 'division', label: 'Division' },
                  { value: 'team', label: 'Team' },
                  { value: 'project', label: 'Project' },
                  { value: 'location', label: 'Location' },
                ]}
                description="Type of organizational unit"
                placeholder="Select a category"
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(ROUTES.DEPARTMENTS)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Create Department
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
