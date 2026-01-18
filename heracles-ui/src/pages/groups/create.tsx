import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { PageHeader, LoadingSpinner } from '@/components/common'
import { useCreateGroup } from '@/hooks'
import { groupCreateSchema, type GroupCreateFormData } from '@/lib/schemas'
import { ROUTES } from '@/config/constants'

export function GroupCreatePage() {
  const navigate = useNavigate()
  const createMutation = useCreateGroup()

  const form = useForm<GroupCreateFormData>({
    resolver: zodResolver(groupCreateSchema),
    defaultValues: {
      cn: '',
      description: '',
    },
  })

  const onSubmit = async (data: GroupCreateFormData) => {
    try {
      await createMutation.mutateAsync(data)
      toast.success(`Group "${data.cn}" created successfully`)
      navigate(ROUTES.GROUPS)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create group')
    }
  }

  return (
    <div>
      <PageHeader
        title="Create Group"
        description="Add a new group to the directory"
        breadcrumbs={[
          { label: 'Groups', href: ROUTES.GROUPS },
          { label: 'New Group' },
        ]}
        actions={
          <Button variant="outline" onClick={() => navigate(ROUTES.GROUPS)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        }
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
          <Card>
            <CardHeader>
              <CardTitle>Group Information</CardTitle>
              <CardDescription>Basic information about the group</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="cn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Group Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="developers" {...field} />
                    </FormControl>
                    <FormDescription>Unique identifier for the group</FormDescription>
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
                      <Input placeholder="Development team members" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="gidNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>GID Number</FormLabel>
                    <FormControl>
                      <Input type="number" placeholder="Auto-generated" {...field} />
                    </FormControl>
                    <FormDescription>Leave empty for auto-generation</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button type="button" variant="outline" onClick={() => navigate(ROUTES.GROUPS)}>
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
                  Create Group
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
