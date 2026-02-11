import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Save, ArrowLeft, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
} from '@/components/ui/form'
import { PageHeader, LoadingSpinner, PasswordRequirements } from '@/components/common'
import { UserFormFields } from '@/components/users'
import { useCreateUser, useTemplates } from '@/hooks'
import { userCreateSchema, type UserCreateFormData } from '@/lib/schemas'
import { AppError } from '@/lib/errors'
import { ROUTES } from '@/config/constants'
import { useDepartmentStore } from '@/stores'
import { useState, useEffect, useRef } from 'react'

/** Maps LDAP attribute names from template defaults to form field names */
const TEMPLATE_FIELD_MAP: Record<string, keyof UserCreateFormData> = {
  uid: 'uid',
  givenName: 'givenName',
  sn: 'sn',
  mail: 'mail',
  telephoneNumber: 'telephoneNumber',
  title: 'title',
  description: 'description',
  displayName: 'displayName',
  labeledURI: 'labeledURI',
  preferredLanguage: 'preferredLanguage',
  mobile: 'mobile',
  facsimileTelephoneNumber: 'facsimileTelephoneNumber',
  street: 'street',
  postalAddress: 'postalAddress',
  l: 'l',
  st: 'st',
  postalCode: 'postalCode',
  c: 'c',
  roomNumber: 'roomNumber',
  o: 'o',
  ou: 'organizationalUnit',
  organizationalUnit: 'organizationalUnit',
  departmentNumber: 'departmentNumber',
  employeeNumber: 'employeeNumber',
  employeeType: 'employeeType',
  manager: 'manager',
}

const EMPTY_DEFAULTS: UserCreateFormData = {
  uid: '',
  givenName: '',
  sn: '',
  mail: '',
  telephoneNumber: '',
  title: '',
  description: '',
  displayName: '',
  labeledURI: '',
  preferredLanguage: '',
  mobile: '',
  facsimileTelephoneNumber: '',
  street: '',
  postalAddress: '',
  l: '',
  st: '',
  postalCode: '',
  c: '',
  roomNumber: '',
  o: '',
  organizationalUnit: '',
  departmentNumber: '',
  employeeNumber: '',
  employeeType: '',
  manager: '',
  password: '',
  confirmPassword: '',
}

export function UserCreatePage() {
  const navigate = useNavigate()
  const createMutation = useCreateUser()
  const { currentBase } = useDepartmentStore()
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const { data: templateList } = useTemplates(currentBase || undefined)
  const templates = templateList?.templates ?? []
  const prevTemplateId = useRef<string>('')

  const form = useForm<UserCreateFormData>({
    resolver: zodResolver(userCreateSchema),
    defaultValues: EMPTY_DEFAULTS,
  })

  // Pre-fill form fields when a template is selected
  useEffect(() => {
    if (selectedTemplateId === prevTemplateId.current) return
    prevTemplateId.current = selectedTemplateId

    if (!selectedTemplateId) {
      // Cleared template — reset to blank (preserve password fields)
      const pw = form.getValues('password')
      const cpw = form.getValues('confirmPassword')
      form.reset({ ...EMPTY_DEFAULTS, password: pw, confirmPassword: cpw })
      return
    }

    const tmpl = templates.find((t) => t.id === selectedTemplateId)
    if (!tmpl) return

    // Start from blank defaults
    const values: Record<string, string> = {}
    for (const [ldapAttr, val] of Object.entries(tmpl.defaults)) {
      if (ldapAttr === 'objectClasses' || ldapAttr === 'objectClass') continue
      const formField = TEMPLATE_FIELD_MAP[ldapAttr]
      if (formField && typeof val === 'string') {
        values[formField] = val
      }
    }

    // Apply to form — keep password untouched
    const pw = form.getValues('password')
    const cpw = form.getValues('confirmPassword')
    form.reset({
      ...EMPTY_DEFAULTS,
      ...values,
      password: pw,
      confirmPassword: cpw,
    })

    toast.success(`Template "${tmpl.name}" applied`)
  }, [selectedTemplateId, templates, form])

  const onSubmit = async (data: UserCreateFormData) => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { confirmPassword, ...userData } = data
      // Compute cn (common name) from givenName and sn
      const cn = `${userData.givenName} ${userData.sn}`.trim()
      // Include department context if a department is selected
      await createMutation.mutateAsync({
        ...userData,
        cn,
        departmentDn: currentBase || undefined,
        templateId: selectedTemplateId || undefined,
      })
      toast.success(`User "${data.uid}" created successfully`)
      navigate(ROUTES.USERS)
    } catch (error) {
      AppError.toastError(error, 'Failed to create user')
    }
  }

  return (
    <div>
      <PageHeader
        title="Create User"
        description="Add a new user to the directory"
        actions={
          <Button variant="outline" onClick={() => navigate(ROUTES.USERS)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        }
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {templates.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Template
                </CardTitle>
                <CardDescription>
                  Apply a template to pre-configure defaults and activate plugins
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={selectedTemplateId || '__none__'}
                  onValueChange={(val) => setSelectedTemplateId(val === '__none__' ? '' : val)}
                >
                  <SelectTrigger className="w-full md:w-[320px]">
                    <SelectValue placeholder="No template (manual setup)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">No template</SelectItem>
                    {templates.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                        {t.description ? ` — ${t.description}` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>User identity and contact information</CardDescription>
            </CardHeader>
            <CardContent>
              <UserFormFields control={form.control} mode="create" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Password</CardTitle>
              <CardDescription>Set the initial password for this user</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <PasswordRequirements />
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password *</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="••••••••" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Confirm Password *</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="••••••••" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button type="button" variant="outline" onClick={() => navigate(ROUTES.USERS)}>
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
                  Create User
                </>
              )}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  )
}
