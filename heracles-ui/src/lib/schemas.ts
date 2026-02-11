import { z } from 'zod'

// Auth schemas
export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

export type LoginFormData = z.infer<typeof loginSchema>

// User schemas
export const userSchema = z.object({
  uid: z.string().min(1, 'Username is required').regex(/^[a-zA-Z][a-zA-Z0-9._-]*$/, 'Invalid username format'),
  givenName: z.string().min(1, 'First name is required'),
  sn: z.string().min(1, 'Last name is required'),
  mail: z.string().email('Invalid email address').optional().or(z.literal('')),
  telephoneNumber: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  // Personal
  displayName: z.string().optional(),
  labeledURI: z.string().url('Invalid URL').optional().or(z.literal('')),
  preferredLanguage: z.string().optional(),
  // Contact
  mobile: z.string().optional(),
  facsimileTelephoneNumber: z.string().optional(),
  // Address
  street: z.string().optional(),
  postalAddress: z.string().optional(),
  l: z.string().optional(),
  st: z.string().optional(),
  postalCode: z.string().optional(),
  c: z.string().max(2, 'Country code must be 2 characters').optional().or(z.literal('')),
  roomNumber: z.string().optional(),
  // Organization
  o: z.string().optional(),
  organizationalUnit: z.string().optional(),
  departmentNumber: z.string().optional(),
  employeeNumber: z.string().optional(),
  employeeType: z.string().optional(),
  manager: z.string().optional(),
})

export const userCreateSchema = userSchema.extend({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

export const userUpdateSchema = userSchema.partial().omit({ uid: true })

export type UserFormData = z.infer<typeof userSchema>
export type UserCreateFormData = z.infer<typeof userCreateSchema>
export type UserUpdateFormData = z.infer<typeof userUpdateSchema>

// Group schemas
export const groupSchema = z.object({
  cn: z.string().min(1, 'Group name is required').regex(/^[a-zA-Z][a-zA-Z0-9._-]*$/, 'Invalid group name format'),
  description: z.string().optional(),
})

export const groupCreateSchema = groupSchema
export const groupUpdateSchema = groupSchema.partial().omit({ cn: true })

export type GroupFormData = z.infer<typeof groupSchema>
export type GroupCreateFormData = z.infer<typeof groupCreateSchema>
export type GroupUpdateFormData = z.infer<typeof groupUpdateSchema>

// Password schemas
export const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

export type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>

export const setPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

export type SetPasswordFormData = z.infer<typeof setPasswordSchema>

// Department schemas
export const departmentSchema = z.object({
  ou: z.string()
    .min(1, 'Department name is required')
    .max(64, 'Department name must be at most 64 characters')
    .regex(/^[a-zA-Z0-9._-]+$/, 'Invalid department name format'),
  description: z.string().max(256).optional(),
  parentDn: z.string().optional(),
  hrcDepartmentCategory: z.string().max(64).optional(),
  hrcDepartmentManager: z.string().optional(),
})

export const departmentCreateSchema = departmentSchema
export const departmentUpdateSchema = departmentSchema.partial().omit({ ou: true, parentDn: true })

export type DepartmentFormData = z.infer<typeof departmentSchema>
export type DepartmentCreateFormData = z.infer<typeof departmentCreateSchema>
export type DepartmentUpdateFormData = z.infer<typeof departmentUpdateSchema>

// Role schemas
export const roleSchema = z.object({
  cn: z.string().min(1, 'Role name is required').regex(/^[a-zA-Z][a-zA-Z0-9._-]*$/, 'Invalid role name format'),
  description: z.string().optional(),
})

export const roleCreateSchema = roleSchema
export const roleUpdateSchema = roleSchema.partial().omit({ cn: true })

export type RoleFormData = z.infer<typeof roleSchema>
export type RoleCreateFormData = z.infer<typeof roleCreateSchema>
export type RoleUpdateFormData = z.infer<typeof roleUpdateSchema>

// ACL Policy schemas
export const policyCreateSchema = z.object({
  name: z.string().min(1, 'Policy name is required').max(128, 'Policy name must be at most 128 characters'),
  description: z.string().max(1024).optional(),
  permissions: z.array(z.string()).min(1, 'At least one permission is required'),
})

export const policyUpdateSchema = z.object({
  name: z.string().min(1).max(128).optional(),
  description: z.string().max(1024).optional(),
  permissions: z.array(z.string()).min(1).optional(),
})

export type PolicyCreateFormData = z.infer<typeof policyCreateSchema>
export type PolicyUpdateFormData = z.infer<typeof policyUpdateSchema>

// ACL Assignment schemas
export const assignmentCreateSchema = z.object({
  policyId: z.string().uuid('Invalid policy ID'),
  subjectType: z.enum(['user', 'group', 'role'], { required_error: 'Subject type is required' }),
  subjectDn: z.string().min(1, 'Subject DN is required'),
  scopeDn: z.string().default(''),
  scopeType: z.enum(['base', 'subtree']).default('subtree'),
  selfOnly: z.boolean().default(false),
  deny: z.boolean().default(false),
  priority: z.coerce.number().int().min(0).max(1000).default(0),
})

export type AssignmentCreateFormData = z.infer<typeof assignmentCreateSchema>

// ACL Attribute Rule schemas
export const attrRuleCreateSchema = z.object({
  objectType: z.string().min(1, 'Object type is required'),
  action: z.enum(['read', 'write'], { required_error: 'Action is required' }),
  ruleType: z.enum(['allow', 'deny'], { required_error: 'Rule type is required' }),
  attrGroups: z.array(z.string()).min(1, 'At least one attribute group is required'),
})

export type AttrRuleCreateFormData = z.infer<typeof attrRuleCreateSchema>

// Template schemas
const jsonString = z.string().refine(
  (val) => {
    if (!val.trim()) return true
    try { JSON.parse(val); return true } catch { return false }
  },
  { message: 'Invalid JSON' },
)

export const templateCreateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(128),
  description: z.string().max(512).optional(),
  defaults: jsonString.refine((val) => val.trim().length > 0, { message: 'Defaults JSON is required' }),
})

export const templateUpdateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(128),
  description: z.string().max(512).optional(),
  defaults: jsonString.refine((val) => val.trim().length > 0, { message: 'Defaults JSON is required' }),
  variables: jsonString,
  departmentDn: z.string().optional(),
  displayOrder: z.coerce.number().int().min(0).default(0),
})

export type TemplateCreateFormData = z.infer<typeof templateCreateSchema>
export type TemplateUpdateFormData = z.infer<typeof templateUpdateSchema>

