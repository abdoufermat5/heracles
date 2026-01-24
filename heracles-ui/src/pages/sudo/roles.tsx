/**
 * Sudo Roles List Page
 *
 * Lists all sudo roles and provides CRUD operations.
 */

import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Shield, RefreshCw, Search } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

import { DeleteDialog } from '@/components/common'
import { CreateSudoRoleDialog, SudoRolesTable } from '@/components/plugins/sudo'

import { useSudoRoles, useDeleteSudoRole } from '@/hooks/use-sudo'
import type { SudoRoleData } from '@/types/sudo'

export function SudoRolesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [roleToDelete, setRoleToDelete] = useState<SudoRoleData | null>(null)

  // Open create dialog if ?create=true is in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setShowCreateDialog(true)
      searchParams.delete('create')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const { data: rolesResponse, isLoading, error, refetch } = useSudoRoles()
  const deleteMutation = useDeleteSudoRole()

  // Filter roles by search query (exclude defaults)
  const filteredRoles =
    rolesResponse?.roles?.filter((role) => {
      if (role.isDefault) return false // Hide defaults from main list
      const matchesSearch =
        role.cn.toLowerCase().includes(searchQuery.toLowerCase()) ||
        role.description?.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesSearch
    }) ?? []

  const handleDelete = async () => {
    if (!roleToDelete) return

    try {
      await deleteMutation.mutateAsync(roleToDelete.cn)
      toast.success(`Sudo role "${roleToDelete.cn}" deleted successfully`)
      setRoleToDelete(null)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete sudo role'
      )
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load sudo roles</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Sudo Roles
          </h1>
          <p className="text-muted-foreground">
            Manage sudo rules for privilege escalation on UNIX/Linux systems
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Role
        </Button>
      </div>

      {/* Search and Stats */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search roles..."
            className="pl-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Badge variant="secondary">
          {filteredRoles.length} role{filteredRoles.length !== 1 ? 's' : ''}
        </Badge>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Roles Table */}
      <Card>
        <CardHeader>
          <CardTitle>Sudo Roles</CardTitle>
          <CardDescription>
            Configure who can run what commands with elevated privileges
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredRoles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchQuery
                ? 'No roles match your search'
                : 'No sudo roles found. Create one to get started.'}
            </div>
          ) : (
            <SudoRolesTable roles={filteredRoles} onDelete={setRoleToDelete} />
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <CreateSudoRoleDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />

      {/* Delete Confirmation */}
      <DeleteDialog
        open={!!roleToDelete}
        onOpenChange={(open) => !open && setRoleToDelete(null)}
        itemName={roleToDelete?.cn ?? ''}
        itemType="sudo role"
        description={`Are you sure you want to delete the sudo role "${roleToDelete?.cn}"? This will remove all associated sudo privileges. This action cannot be undone.`}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
