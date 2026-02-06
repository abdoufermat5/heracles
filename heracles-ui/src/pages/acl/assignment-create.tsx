import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form'
import { PageHeader, LoadingSpinner } from '@/components/common'
import { SubjectDnPicker } from '@/components/acl'
import { useCreateAssignment, useAclPolicies } from '@/hooks'
import { assignmentCreateSchema, type AssignmentCreateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'

export function AclAssignmentCreatePage() {
  const navigate = useNavigate()
  const createMutation = useCreateAssignment()
  const { data: policiesData, isLoading: policiesLoading } = useAclPolicies({ page_size: 200 })

  const form = useForm<AssignmentCreateFormData>({
    resolver: zodResolver(assignmentCreateSchema),
    defaultValues: {
      policyId: '',
      subjectType: 'user',
      subjectDn: '',
      scopeDn: '',
      scopeType: 'subtree',
      selfOnly: false,
      deny: false,
      priority: 0,
    },
  })

  const watchedSubjectType = form.watch('subjectType')

  const onSubmit = async (data: AssignmentCreateFormData) => {
    try {
      await createMutation.mutateAsync(data)
      toast.success('Assignment created successfully')
      navigate(ROUTES.ACL_ASSIGNMENTS)
    } catch (error) {
      AppError.toastError(error, 'Failed to create assignment')
    }
  }

  return (
    <div>
      <PageHeader
        title={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ACL_ASSIGNMENTS)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            Create Assignment
          </div>
        }
        description="Assign a policy to a user, group, or role"
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Policy</CardTitle>
              <CardDescription>Select the policy to assign</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="policyId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Policy</FormLabel>
                    {policiesLoading ? (
                      <LoadingSpinner />
                    ) : (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a policy" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {policiesData?.policies.map((policy) => (
                            <SelectItem key={policy.id} value={policy.id}>
                              <div className="flex items-center gap-2">
                                {policy.name}
                                <span className="text-muted-foreground text-xs">
                                  ({policy.permissions.length} permissions)
                                </span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Subject</CardTitle>
              <CardDescription>Who receives this policy assignment</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="subjectType"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subject Type</FormLabel>
                    <Select
                      onValueChange={(val) => {
                        field.onChange(val)
                        // Reset subjectDn when type changes
                        form.setValue('subjectDn', '')
                      }}
                      value={field.value}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="user">User</SelectItem>
                        <SelectItem value="group">Group</SelectItem>
                        <SelectItem value="role">Role</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      {watchedSubjectType === 'user' && 'The specific user to grant permissions to'}
                      {watchedSubjectType === 'group' && 'All members of this group will receive the permissions'}
                      {watchedSubjectType === 'role' && 'All occupants of this role will receive the permissions'}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="subjectDn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subject</FormLabel>
                    <FormControl>
                      <SubjectDnPicker
                        subjectType={watchedSubjectType as 'user' | 'group' | 'role'}
                        value={field.value}
                        onChange={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Scope & Options</CardTitle>
              <CardDescription>Define where and how the assignment applies</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="scopeDn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Scope DN</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Leave empty for global scope"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Restrict permissions to this subtree. Empty means global (entire directory).
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="scopeType"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Scope Type</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="subtree">Subtree (includes children)</SelectItem>
                          <SelectItem value="base">Base (exact DN only)</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Priority</FormLabel>
                      <FormControl>
                        <Input type="number" min={0} max={1000} {...field} />
                      </FormControl>
                      <FormDescription>Higher = evaluated later</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <FormField
                  control={form.control}
                  name="selfOnly"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-3">
                      <div className="space-y-0.5">
                        <FormLabel>Self Only</FormLabel>
                        <FormDescription className="text-xs">
                          Only applies when the target is the subject&apos;s own entry
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="deny"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-3 border-destructive/20">
                      <div className="space-y-0.5">
                        <FormLabel className="text-destructive">Deny</FormLabel>
                        <FormDescription className="text-xs">
                          Negates all permissions in the policy (deny always wins)
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => navigate(ROUTES.ACL_ASSIGNMENTS)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              Create Assignment
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
