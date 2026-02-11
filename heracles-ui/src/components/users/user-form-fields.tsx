import type { Control, FieldValues, FieldPath } from 'react-hook-form'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { FormInput, FormTextarea, FormPhotoUpload } from '@/components/common/forms'
import type { UserCreateFormData, UserUpdateFormData } from '@/lib/schemas'

// Union type covering both create & edit schemas — all user fields are present in both
type UserFields = UserCreateFormData | UserUpdateFormData

export interface UserFormFieldsProps<T extends FieldValues = UserFields> {
  control: Control<T>
  /** 'create' shows uid (editable), 'edit' hides uid (shown separately as read-only) */
  mode: 'create' | 'edit'
  disabled?: boolean
}

/**
 * Shared user form fields used by both the create and edit pages.
 *
 * - **Basic Information** — always visible
 * - **Contact** — collapsed by default
 * - **Address** — collapsed by default
 * - **Organization** — collapsed by default
 * - **Personal** — collapsed by default (includes photo upload)
 *
 * Uses the shared `FormInput` / `FormTextarea` / `FormPhotoUpload` wrappers
 * to eliminate per-field boilerplate.
 */
export function UserFormFields<T extends FieldValues = UserFields>({
  control,
  mode,
  disabled,
}: UserFormFieldsProps<T>) {
  // Helper to cast name for generic control
  const n = (name: string) => name as FieldPath<T>

  return (
    <div className="space-y-4">
      {/* ── Basic Information (always visible) ── */}
      <div className="grid gap-4 md:grid-cols-2">
        {mode === 'create' && (
          <FormInput
            control={control}
            name={n('uid')}
            label="Username *"
            placeholder="jdoe"
            description="Unique login identifier"
            disabled={disabled}
          />
        )}

        <FormInput
          control={control}
          name={n('mail')}
          label="Email"
          type="email"
          placeholder="john.doe@example.com"
          disabled={disabled}
        />

        <FormInput
          control={control}
          name={n('givenName')}
          label="First Name *"
          placeholder="John"
          disabled={disabled}
        />

        <FormInput
          control={control}
          name={n('sn')}
          label="Last Name *"
          placeholder="Doe"
          disabled={disabled}
        />

        <FormInput
          control={control}
          name={n('displayName')}
          label="Display Name"
          placeholder="John Doe"
          disabled={disabled}
        />

        <FormTextarea
          control={control}
          name={n('description')}
          label="Description"
          placeholder="Brief description…"
          rows={2}
          disabled={disabled}
          className="md:col-span-2"
        />
      </div>

      {/* ── Collapsible optional sections ── */}
      <Accordion type="multiple" className="w-full">
        {/* Contact */}
        <AccordionItem value="contact">
          <AccordionTrigger>Contact</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 md:grid-cols-2 pt-2">
              <FormInput
                control={control}
                name={n('telephoneNumber')}
                label="Phone"
                placeholder="+1 234 567 8900"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('mobile')}
                label="Mobile"
                placeholder="+1 234 567 8901"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('facsimileTelephoneNumber')}
                label="Fax"
                placeholder="+1 234 567 8902"
                disabled={disabled}
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Address */}
        <AccordionItem value="address">
          <AccordionTrigger>Address</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 md:grid-cols-2 pt-2">
              <FormInput
                control={control}
                name={n('street')}
                label="Street"
                placeholder="123 Main St"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('postalAddress')}
                label="Postal Address"
                placeholder="PO Box 456"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('l')}
                label="City"
                placeholder="San Francisco"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('st')}
                label="State / Province"
                placeholder="California"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('postalCode')}
                label="Postal Code"
                placeholder="94105"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('c')}
                label="Country"
                placeholder="US"
                description="2-letter country code"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('roomNumber')}
                label="Room Number"
                placeholder="B-401"
                disabled={disabled}
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Organization */}
        <AccordionItem value="organization">
          <AccordionTrigger>Organization</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 md:grid-cols-2 pt-2">
              <FormInput
                control={control}
                name={n('title')}
                label="Job Title"
                placeholder="Software Engineer"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('o')}
                label="Organization"
                placeholder="Acme Corp"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('organizationalUnit')}
                label="Organizational Unit"
                placeholder="Engineering"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('departmentNumber')}
                label="Department Number"
                placeholder="D-42"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('employeeNumber')}
                label="Employee Number"
                placeholder="EMP-1234"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('employeeType')}
                label="Employee Type"
                placeholder="Full-time"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('manager')}
                label="Manager"
                placeholder="uid=manager,ou=people,dc=example,dc=com"
                description="DN of the manager"
                disabled={disabled}
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Personal */}
        <AccordionItem value="personal">
          <AccordionTrigger>Personal</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 md:grid-cols-2 pt-2">
              <FormPhotoUpload
                control={control}
                name={n('jpegPhoto') as FieldPath<T>}
                label="Photo"
                description="JPEG photo (max 512 KB, will be resized)"
                disabled={disabled}
                className="md:col-span-2"
              />
              <FormInput
                control={control}
                name={n('labeledURI')}
                label="Homepage"
                type="url"
                placeholder="https://example.com"
                disabled={disabled}
              />
              <FormInput
                control={control}
                name={n('preferredLanguage')}
                label="Preferred Language"
                placeholder="en"
                disabled={disabled}
              />
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
