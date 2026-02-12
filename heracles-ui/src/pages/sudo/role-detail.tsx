/**
 * Sudo Role Detail Page
 *
 * View and edit a single sudo role.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Shield, Save, Trash2, RefreshCw, Users, Terminal, Settings } from 'lucide-react'
import { toast } from 'sonner'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Form } from '@/components/ui/form'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { DeleteDialog } from '@/components/common'
import {
  SudoRoleGeneralTab,
  SudoRoleAccessTab,
  SudoRoleCommandsTab,
  SudoRoleOptionsTab,
} from '@/components/plugins/sudo'

import { useSudoRole, useUpdateSudoRole, useDeleteSudoRole } from '@/hooks/use-sudo'
import { arrayToString, stringToArray } from '@/lib/string-helpers'
import { AppError } from '@/lib/errors'
import { PLUGIN_ROUTES } from '@/config/routes'
import { useDepartmentStore } from '@/stores'

// Form schema for editing the role
const editSchema = z.object({
  description: z.string().max(255).optional(),
  sudoUser: z.string().optional(),
  sudoHost: z.string().optional(),
  sudoCommand: z.string().optional(),
  sudoRunAsUser: z.string().optional(),
  sudoRunAsGroup: z.string().optional(),
  sudoOption: z.array(z.string()).optional(),
  sudoOrder: z.number().min(0).optional(),
  sudoNotBefore: z.string().optional(),
  sudoNotAfter: z.string().optional(),
})

type EditFormData = z.infer<typeof editSchema>

export function SudoRoleDetailPage() {
  const { cn } = useParams<{ cn: string }>()
  const navigate = useNavigate()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const { currentBase } = useDepartmentStore()

  const { data: role, isLoading, error, refetch } = useSudoRole(cn!, {
    baseDn: currentBase || undefined
  })
  const updateMutation = useUpdateSudoRole()
  const deleteMutation = useDeleteSudoRole()

  const form = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
  })

  // Reset form when role data loads
  useEffect(() => {
    if (role) {
      form.reset({
        description: role.description ?? '',
        sudoUser: arrayToString(role.sudoUser),
        sudoHost: arrayToString(role.sudoHost),
        sudoCommand: arrayToString(role.sudoCommand),
        sudoRunAsUser: arrayToString(role.sudoRunAsUser),
        sudoRunAsGroup: arrayToString(role.sudoRunAsGroup),
        sudoOption: role.sudoOption ?? [],
        sudoOrder: role.sudoOrder ?? 0,
        sudoNotBefore: role.sudoNotBefore ?? '',
        sudoNotAfter: role.sudoNotAfter ?? '',
      })
    }
  }, [role, form])

  const hasChanges = form.formState.isDirty

  const handleUpdate = async (data: EditFormData) => {
    try {
      await updateMutation.mutateAsync({
        cn: cn!,
        data: {
          description: data.description || undefined,
          sudoUser: stringToArray(data.sudoUser),
          sudoHost: stringToArray(data.sudoHost),
          sudoCommand: stringToArray(data.sudoCommand),
          sudoRunAsUser: stringToArray(data.sudoRunAsUser),
          sudoRunAsGroup: stringToArray(data.sudoRunAsGroup),
          sudoOption: data.sudoOption,
          sudoOrder: data.sudoOrder,
          sudoNotBefore: data.sudoNotBefore || undefined,
          sudoNotAfter: data.sudoNotAfter || undefined,
        },
        baseDn: currentBase || undefined,
      })
      toast.success('Sudo role updated successfully')
      form.reset(data)
    } catch (error) {
      AppError.toastError(error, 'Failed to update sudo role')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({
        cn: cn!,
        baseDn: currentBase || undefined
      })
      toast.success('Sudo role deleted successfully')
      navigate(PLUGIN_ROUTES.SUDO.ROLES)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete sudo role')
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (error || !role) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-destructive">
              <p>Failed to load sudo role</p>
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to={PLUGIN_ROUTES.SUDO.ROLES}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Roles
                  </Link>
                </Button>
              </div>
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
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to={PLUGIN_ROUTES.SUDO.ROLES}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Shield className="h-6 w-6" />
              {role.cn}
            </h1>
            <p className="text-muted-foreground">
              Sudo Role • Priority {role.sudoOrder}
              {role.isDefault && (
                <Badge variant="secondary" className="ml-2">
                  Default
                </Badge>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <Badge variant="outline" className="text-yellow-600">
              Unsaved changes
            </Badge>
          )}
          <Button variant="destructive" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleUpdate)}>
          <Tabs defaultValue="general" className="space-y-6">
            <TabsList>
              <TabsTrigger value="general">
                <Settings className="h-4 w-4 mr-2" />
                General
              </TabsTrigger>
              <TabsTrigger value="access">
                <Users className="h-4 w-4 mr-2" />
                Access Control
              </TabsTrigger>
              <TabsTrigger value="commands">
                <Terminal className="h-4 w-4 mr-2" />
                Commands
              </TabsTrigger>
              <TabsTrigger value="options">
                <Shield className="h-4 w-4 mr-2" />
                Options
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-6">
              <SudoRoleGeneralTab control={form.control} roleName={role.cn} />
            </TabsContent>

            <TabsContent value="access" className="space-y-6">
              <SudoRoleAccessTab control={form.control} role={role} />
            </TabsContent>

            <TabsContent value="commands" className="space-y-6">
              <SudoRoleCommandsTab form={form} role={role} />
            </TabsContent>

            <TabsContent value="options" className="space-y-6">
              <SudoRoleOptionsTab control={form.control} role={role} />
            </TabsContent>
          </Tabs>

          {/* Save Button - Fixed at bottom */}
          <div className="sticky bottom-4 flex justify-end pt-4">
            <Button
              type="submit"
              disabled={updateMutation.isPending || !hasChanges}
              className="shadow-lg"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </Form>

      {/* Delete Confirmation */}
      <DeleteDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        itemName={role.cn}
        itemType="sudo role"
        description={`Are you sure you want to delete the sudo role "${role.cn}"? This will remove all associated sudo privileges. This action cannot be undone.`}
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
