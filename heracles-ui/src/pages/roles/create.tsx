import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, Shield } from 'lucide-react'
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
import { useCreateRole } from '@/hooks/use-roles'
import { roleCreateSchema, type RoleCreateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'

export function RoleCreatePage() {
    const navigate = useNavigate()
    const createMutation = useCreateRole()

    const form = useForm<RoleCreateFormData>({
        resolver: zodResolver(roleCreateSchema),
        defaultValues: {
            cn: '',
            description: '',
        },
    })

    const onSubmit = async (data: RoleCreateFormData) => {
        try {
            await createMutation.mutateAsync(data)
            toast.success(`Role "${data.cn}" created successfully`)
            navigate(ROUTES.GROUPS)
        } catch (error) {
            AppError.toastError(error, 'Failed to create role')
        }
    }

    return (
        <div>
            <PageHeader
                title="Create Role"
                description="Add a new organizational role to the directory"
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
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5" />
                                Role Information
                            </CardTitle>
                            <CardDescription>Define the role name and description</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <FormField
                                control={form.control}
                                name="cn"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Role Name *</FormLabel>
                                        <FormControl>
                                            <Input placeholder="sysadmin" {...field} />
                                        </FormControl>
                                        <FormDescription>Unique identifier for the role (e.g., sysadmin, helpdesk)</FormDescription>
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
                                            <Input placeholder="System administrator role with elevated permissions" {...field} />
                                        </FormControl>
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
                                    Create Role
                                </>
                            )}
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    )
}
