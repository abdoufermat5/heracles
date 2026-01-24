import type { FieldErrors, FieldValues } from 'react-hook-form'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface FormErrorSummaryProps<T extends FieldValues> {
  errors: FieldErrors<T>
  title?: string
  className?: string
}

interface FlattenedError {
  field: string
  message: string
}

function flattenErrors(
  errors: Record<string, unknown>,
  prefix = ''
): FlattenedError[] {
  const result: FlattenedError[] = []

  for (const [key, value] of Object.entries(errors)) {
    const fieldPath = prefix ? `${prefix}.${key}` : key
    const errorValue = value as { message?: unknown } | undefined

    if (errorValue?.message && typeof errorValue.message === 'string') {
      result.push({ field: fieldPath, message: errorValue.message })
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      // Recursively flatten nested errors
      result.push(...flattenErrors(value as Record<string, unknown>, fieldPath))
    } else if (Array.isArray(value)) {
      // Handle array fields
      value.forEach((item: unknown, index: number) => {
        if (item && typeof item === 'object') {
          result.push(...flattenErrors(item as Record<string, unknown>, `${fieldPath}[${index}]`))
        }
      })
    }
  }

  return result
}

function formatFieldName(field: string): string {
  // Convert camelCase to Title Case with spaces
  return field
    .replace(/\./g, ' > ')
    .replace(/\[(\d+)\]/g, ' $1')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim()
}

/**
 * Displays a summary of form errors at the top of a form
 *
 * @example
 * const form = useForm()
 *
 * return (
 *   <form onSubmit={form.handleSubmit(onSubmit)}>
 *     <FormErrorSummary errors={form.formState.errors} />
 *     {fields}
 *   </form>
 * )
 */
export function FormErrorSummary<T extends FieldValues>({
  errors,
  title = 'Please fix the following errors:',
  className,
}: FormErrorSummaryProps<T>) {
  const errorList = flattenErrors(errors)

  if (errorList.length === 0) {
    return null
  }

  return (
    <Alert variant="destructive" className={className}>
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          {errorList.map(({ field, message }) => (
            <li key={field}>
              <span className="font-medium">{formatFieldName(field)}:</span> {message}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  )
}
