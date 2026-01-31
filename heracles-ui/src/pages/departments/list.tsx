import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Plus, Building2, FolderTree } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { DepartmentsTable } from '@/components/departments'
import { useDepartments, useDeleteDepartment, useDepartmentTree } from '@/hooks'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/routes'
import type { Department } from '@/types'

export function DepartmentsListPage() {
  const navigate = useNavigate()
  const [deleteDepartment, setDeleteDepartment] = useState<Department | null>(null)
  const { setCurrentBase } = useDepartmentStore()

  // Fetch both tree (for total count) and list
  const { data: treeData, isLoading: treeLoading } = useDepartmentTree()
  const { data, isLoading, error, refetch } = useDepartments()
  const deleteMutation = useDeleteDepartment()

  const handleDelete = async () => {
    if (!deleteDepartment) return
    try {
      // Check if department has children
      if (deleteDepartment.childrenCount > 0) {
        // Ask for recursive delete confirmation
        await deleteMutation.mutateAsync({
          dn: deleteDepartment.dn,
          recursive: true,
        })
      } else {
        await deleteMutation.mutateAsync({ dn: deleteDepartment.dn })
      }
      toast.success(`Department "${deleteDepartment.ou}" deleted successfully`)
      setDeleteDepartment(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete department'
      )
    }
  }

  const handleSelect = (department: Department) => {
    setCurrentBase(department.dn, department.path)
    // Navigate to users filtered by this department
    navigate(ROUTES.USERS)
  }

  const isPageLoading = isLoading || treeLoading

  if (isPageLoading) {
    return <LoadingPage message="Loading departments..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Manage organizational units and department hierarchy"
        actions={
          <Button asChild>
            <Link to={ROUTES.DEPARTMENT_CREATE}>
              <Plus className="mr-2 h-4 w-4" />
              New Department
            </Link>
          </Button>
        }
      />

      {/* Tree overview card */}
      {treeData?.tree && treeData.tree.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderTree className="h-5 w-5" />
              Department Hierarchy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">
              {treeData.total} department{treeData.total !== 1 ? 's' : ''}{' '}
              organized in a hierarchical structure.
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            All Departments
            <Badge variant="secondary">{data?.total || 0}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DepartmentsTable
            departments={data?.departments ?? []}
            onDelete={setDeleteDepartment}
            onSelect={handleSelect}
            emptyMessage="No departments found"
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deleteDepartment}
        onOpenChange={(open) => !open && setDeleteDepartment(null)}
        title="Delete Department"
        description={
          deleteDepartment?.childrenCount && deleteDepartment.childrenCount > 0
            ? `Department "${deleteDepartment?.ou}" has ${deleteDepartment?.childrenCount} children. This will delete the department and all its contents. This action cannot be undone.`
            : `Are you sure you want to delete department "${deleteDepartment?.ou}"? This action cannot be undone.`
        }
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
