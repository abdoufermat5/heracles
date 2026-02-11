import { useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Building2, Trash2, MoreHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Form } from '@/components/ui/form'
import { PageHeader, DetailPageSkeleton, LoadingSpinner, ErrorDisplay, ConfirmDialog, FormTextarea, FormSelect } from '@/components/common'
import { useDepartment, useUpdateDepartment, useDeleteDepartment } from '@/hooks'
import { departmentUpdateSchema, type DepartmentUpdateFormData } from '@/lib/schemas'
import { ROUTES, departmentDetailPath } from '@/config/routes'
import { useState, useEffect } from 'react'
import { useRecentStore } from '@/stores'

export function DepartmentDetailPage() {
  const { dn } = useParams<{ dn: string }>()
  const decodedDn = dn ? decodeURIComponent(dn) : ''
  const navigate = useNavigate()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const addRecentItem = useRecentStore((state) => state.addItem)

  const { data: department, isLoading, error, refetch } = useDepartment(decodedDn)
  const updateMutation = useUpdateDepartment(decodedDn)
  const deleteMutation = useDeleteDepartment()

  const form = useForm<DepartmentUpdateFormData>({
    resolver: zodResolver(departmentUpdateSchema),
    defaultValues: {
      description: '',
      hrcDepartmentCategory: '',
      hrcDepartmentManager: '',
    },
  })

  // Update form when department data loads
  useEffect(() => {
    if (department) {
      form.reset({
        description: department.description || '',
        hrcDepartmentCategory: department.hrcDepartmentCategory || '',
        hrcDepartmentManager: department.hrcDepartmentManager || '',
      })
    }
  }, [department, form])

  useEffect(() => {
    if (!department) return
    addRecentItem({
      id: department.dn,
      label: department.ou,
      href: departmentDetailPath(department.dn),
      type: 'department',
      description: department.path,
    })
  }, [addRecentItem, department])

  const onSubmit = async (data: DepartmentUpdateFormData) => {
    try {
      await updateMutation.mutateAsync({
        description: data.description || undefined,
        hrcDepartmentCategory: data.hrcDepartmentCategory || undefined,
        hrcDepartmentManager: data.hrcDepartmentManager || undefined,
      })
      toast.success('Department updated successfully')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to update department'
      )
    }
  }

  const handleDelete = async () => {
    try {
      const recursive = (department?.childrenCount ?? 0) > 0
      await deleteMutation.mutateAsync({ dn: decodedDn, recursive })
      toast.success(`Department "${department?.ou}" deleted successfully`)
      navigate(ROUTES.DEPARTMENTS)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete department'
      )
    }
  }

  if (isLoading) {
    return <DetailPageSkeleton />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  if (!department) {
    return <ErrorDisplay message="Department not found" />
  }

  return (
    <div>
      <PageHeader
        title={department.ou}
        description={department.path}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate(ROUTES.DEPARTMENTS)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  <MoreHorizontal className="mr-2 h-4 w-4" />
                  Actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete department
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />

      <div className="space-y-6">
        {/* Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Department Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4 md:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">DN</dt>
                <dd className="mt-1 font-mono text-sm">{department.dn}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Path</dt>
                <dd className="mt-1">{department.path}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Children</dt>
                <dd className="mt-1">
                  <Badge variant="secondary">{department.childrenCount}</Badge>
                </dd>
              </div>
              {department.parentDn && (
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Parent DN
                  </dt>
                  <dd className="mt-1 font-mono text-sm">{department.parentDn}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>

        {/* Edit Form */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Edit Department</CardTitle>
                <CardDescription>
                  Update department information
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
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
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </form>
        </Form>
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Department"
        description={
          department.childrenCount > 0
            ? `Department "${department.ou}" has ${department.childrenCount} children. This will delete the department and all its contents. This action cannot be undone.`
            : `Are you sure you want to delete department "${department.ou}"? This action cannot be undone.`
        }
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
