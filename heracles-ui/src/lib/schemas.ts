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
