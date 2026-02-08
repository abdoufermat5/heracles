import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Trash2, Lock, MoreHorizontal, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { PageHeader, DetailPageSkeleton, ErrorDisplay, ConfirmDialog } from '@/components/common'
import { PermissionGroupCheckboxes, AttrRulesEditor, AssignmentsTable } from '@/components/acl'
import { useAclPolicy, useUpdatePolicy, useDeletePolicy, useAclAssignments } from '@/hooks'
import { policyUpdateSchema, type PolicyUpdateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import { useRecentStore } from '@/stores'

export function AclPolicyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const addRecentItem = useRecentStore((state) => state.addItem)

  const { data: policy, isLoading, error, refetch } = useAclPolicy(id!)
  const updateMutation = useUpdatePolicy(id!)
  const deleteMutation = useDeletePolicy()

  // Fetch assignments for this policy
  const { data: assignmentsData } = useAclAssignments({ policy_id: id })

  const form = useForm<PolicyUpdateFormData>({
    resolver: zodResolver(policyUpdateSchema),
    values: policy
      ? {
          name: policy.name,
          description: policy.description || '',
          permissions: policy.permissions,
        }
      : undefined,
  })

  useEffect(() => {
    if (!policy) return
    addRecentItem({
      id: policy.id,
      label: policy.name,
      href: ROUTES.ACL_POLICY_DETAIL.replace(':id', policy.id),
      type: 'policy',
      description: policy.description,
    })
  }, [addRecentItem, policy])

  if (isLoading) {
    return <DetailPageSkeleton />
  }

  if (error || !policy) {
    return <ErrorDisplay message={error?.message || 'Policy not found'} onRetry={() => refetch()} />
  }

  const isBuiltin = policy.builtin

  const onSubmit = async (data: PolicyUpdateFormData) => {
    try {
      await updateMutation.mutateAsync({
        name: data.name,
        description: data.description || undefined,
        permissions: data.permissions,
      })
      toast.success('Policy updated successfully')
    } catch (error) {
      AppError.toastError(error, 'Failed to update policy')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(id!)
      toast.success(`Policy "${policy.name}" deleted`)
      navigate(ROUTES.ACL_POLICIES)
    } catch (error) {
      AppError.toastError(error, 'Failed to delete policy')
    }
  }

  return (
    <div>
      <PageHeader
        title={
          <div className="flex items-center gap-3">
            {policy.name}
            {isBuiltin && (
              <Badge variant="secondary" className="gap-1">
                <Lock className="h-3 w-3" />
                Built-in
              </Badge>
            )}
          </div>
        }
        description={policy.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => navigate(ROUTES.ACL_POLICIES)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            {!isBuiltin && (
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
                    Delete policy
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate(ROUTES.ACL_POLICIES)}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Return to policies
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        }
      />

      <Tabs defaultValue="permissions" className="space-y-4">
        <TabsList>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
          <TabsTrigger value="attributes">Attribute Rules</TabsTrigger>
          <TabsTrigger value="assignments">
            Assignments
            {assignmentsData?.total ? (
              <Badge variant="secondary" className="ml-1.5 text-xs">
                {assignmentsData.total}
              </Badge>
            ) : null}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="permissions" className="max-w-4xl">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Policy Details</CardTitle>
                  <CardDescription>
                    {isBuiltin
                      ? 'Built-in policies cannot be modified'
                      : 'Update policy name, description, and permissions'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input {...field} disabled={isBuiltin} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea {...field} disabled={isBuiltin} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Permissions</CardTitle>
                  <CardDescription>
                    Permissions granted by this policy
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="permissions"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <PermissionGroupCheckboxes
                            selected={field.value ?? []}
                            onChange={field.onChange}
                            disabled={isBuiltin}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              {!isBuiltin && (
                <div className="flex justify-end">
                  <Button type="submit" disabled={updateMutation.isPending}>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </Button>
                </div>
              )}
            </form>
          </Form>
        </TabsContent>

        <TabsContent value="attributes" className="max-w-4xl">
          <Card>
            <CardHeader>
              <CardTitle>Attribute-Level Access Control</CardTitle>
              <CardDescription>
                Fine-grained control over which attribute groups are accessible.
                If no rules are defined, all attributes are accessible.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AttrRulesEditor policyId={id!} readOnly={isBuiltin} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assignments" className="max-w-4xl">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Assignments Using This Policy</CardTitle>
                <Button
                  size="sm"
                  onClick={() => navigate(`${ROUTES.ACL_ASSIGNMENT_CREATE}?policyId=${policy.id}`)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Assignment
                </Button>
              </div>
              <CardDescription>
                Users, groups, and roles that have been assigned this policy
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AssignmentsTable
                assignments={assignmentsData?.assignments ?? []}
                emptyMessage="No assignments found for this policy"
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Policy"
        description={`Are you sure you want to delete "${policy.name}"? All assignments using this policy will also be deleted. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}
