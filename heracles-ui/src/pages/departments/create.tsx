import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader, LoadingSpinner } from '@/components/common'
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
              <FormField
                control={form.control}
                name="ou"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="Engineering" {...field} />
                    </FormControl>
                    <FormDescription>
                      Unique identifier for the department
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="parentDn"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Parent Department</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(val === "__root__" ? "" : val)}
                      defaultValue={field.value || "__root__"}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Root (no parent)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="__root__">Root (no parent)</SelectItem>
                        {parentOptions.map((opt) => (
                          <SelectItem key={opt.dn} value={opt.dn}>
                            {opt.path}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Optional parent department for hierarchy
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem className="md:col-span-2">
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter a description for this department..."
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="hrcDepartmentCategory"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(val === "__none__" ? "" : val)}
                      defaultValue={field.value || "__none__"}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="__none__">None</SelectItem>
                        <SelectItem value="division">Division</SelectItem>
                        <SelectItem value="team">Team</SelectItem>
                        <SelectItem value="project">Project</SelectItem>
                        <SelectItem value="location">Location</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Type of organizational unit
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
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
