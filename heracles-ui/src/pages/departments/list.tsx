import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Building2, FolderTree, List, Network } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader, ErrorDisplay, ConfirmDialog, ListPageSkeleton } from '@/components/common'
import { DepartmentsTable, DepartmentTree } from '@/components/departments'
import { useDepartments, useDeleteDepartment, useDepartmentTree, useDeleteConfirmation } from '@/hooks'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/routes'
import type { Department } from '@/types'

export function DepartmentsListPage() {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<'tree' | 'list'>('tree')
  const { currentBase, setCurrentBase } = useDepartmentStore()

  // Fetch both tree (for total count) and list
  const { data: treeData, isLoading: treeLoading } = useDepartmentTree()
  const { data, isLoading, error, refetch } = useDepartments()
  const deleteMutation = useDeleteDepartment()

  const deleteConfirmation = useDeleteConfirmation<Department>({
    onDelete: async (department) => {
      if (department.childrenCount > 0) {
        await deleteMutation.mutateAsync({
          dn: department.dn,
          recursive: true,
        })
      } else {
        await deleteMutation.mutateAsync({ dn: department.dn })
      }
    },
    getItemName: (department) => department.ou,
    entityType: 'Department',
    successMessage: (department) => `Department "${department.ou}" deleted successfully`,
    getDescription: (department) =>
      department.childrenCount > 0
        ? `Department "${department.ou}" has ${department.childrenCount} children. This will delete the department and all its contents. This action cannot be undone.`
        : `Are you sure you want to delete department "${department.ou}"? This action cannot be undone.`,
  })

  const handleSelect = (department: Department) => {
    setCurrentBase(department.dn, department.path)
    // Navigate to users filtered by this department
    navigate(ROUTES.USERS)
  }

  const handleTreeSelect = (node: { id: string; path: string }) => {
    setCurrentBase(node.id, node.path)
  }

  const isPageLoading = isLoading || treeLoading

  if (isPageLoading) {
    return <ListPageSkeleton />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            Departments
            <Badge variant="secondary">{treeData?.total || data?.total || 0}</Badge>
          </span>
        }
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

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Building2 className="h-4 w-4" />
          Browse departments by tree or list view
        </div>
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'tree' | 'list')}>
          <TabsList className="h-8">
            <TabsTrigger value="tree" className="h-7 px-3">
              <Network className="h-4 w-4 mr-1.5" />
              Tree
            </TabsTrigger>
            <TabsTrigger value="list" className="h-7 px-3">
              <List className="h-4 w-4 mr-1.5" />
              List
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {viewMode === 'tree' ? (
        treeData?.tree && treeData.tree.length > 0 ? (
          <div className="border rounded-lg p-2 bg-muted/30">
            <DepartmentTree
              data={treeData.tree}
              selectedDn={currentBase || undefined}
              onSelect={handleTreeSelect}
              defaultExpandAll
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <FolderTree className="h-12 w-12 mb-4 opacity-30" />
            <p className="text-sm">No departments found</p>
            <p className="text-xs mt-1">Create your first department to get started</p>
            <Button asChild className="mt-4" size="sm">
              <Link to={ROUTES.DEPARTMENT_CREATE}>
                <Plus className="mr-2 h-4 w-4" />
                New Department
              </Link>
            </Button>
          </div>
        )
      ) : (
        <DepartmentsTable
          departments={data?.departments ?? []}
          onDelete={deleteConfirmation.requestDelete}
          onSelect={handleSelect}
          emptyMessage="No departments found"
        />
      )}

      <ConfirmDialog {...deleteConfirmation.dialogProps} />
    </div>
  )
}
