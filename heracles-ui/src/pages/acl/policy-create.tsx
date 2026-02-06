import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form'
import { PageHeader } from '@/components/common'
import { PermissionGroupCheckboxes } from '@/components/acl'
import { useCreatePolicy } from '@/hooks'
import { policyCreateSchema, type PolicyCreateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES, aclPolicyDetailPath } from '@/config/constants'

export function AclPolicyCreatePage() {
  const navigate = useNavigate()
  const createMutation = useCreatePolicy()

  const form = useForm<PolicyCreateFormData>({
    resolver: zodResolver(policyCreateSchema),
    defaultValues: {
      name: '',
      description: '',
      permissions: [],
    },
  })

  const onSubmit = async (data: PolicyCreateFormData) => {
    try {
      const result = await createMutation.mutateAsync({
        name: data.name,
        description: data.description || undefined,
        permissions: data.permissions,
      })
      toast.success(`Policy "${data.name}" created successfully`)
      navigate(aclPolicyDetailPath(result.id))
    } catch (error) {
      AppError.toastError(error, 'Failed to create policy')
    }
  }

  return (
    <div>
      <PageHeader
        title={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ACL_POLICIES)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            Create Policy
          </div>
        }
        description="Create a new access control policy with a set of permissions"
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Policy Details</CardTitle>
              <CardDescription>Basic information about the policy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., User Manager" {...field} />
                    </FormControl>
                    <FormDescription>A unique name for this policy</FormDescription>
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
                      <Textarea
                        placeholder="Describe what this policy grants access to..."
                        {...field}
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
              <CardTitle>Permissions</CardTitle>
              <CardDescription>
                Select the permissions this policy grants. Permissions are grouped by scope.
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
                        selected={field.value}
                        onChange={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => navigate(ROUTES.ACL_POLICIES)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              Create Policy
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
