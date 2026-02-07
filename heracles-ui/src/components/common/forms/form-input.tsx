import {
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import type { Control, FieldPath, FieldValues } from 'react-hook-form'

export interface FormInputProps<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> {
    control: Control<TFieldValues>
    name: TName
    label: string
    placeholder?: string
    description?: string
    disabled?: boolean
    type?: 'text' | 'email' | 'password' | 'number' | 'url'
    className?: string
    autoComplete?: string
}

/**
 * Wrapper around FormField + Input that reduces boilerplate.
 * 
 * @example
 * ```tsx
 * // Before: 12 lines
 * <FormField
 *   control={form.control}
 *   name="email"
 *   render={({ field }) => (
 *     <FormItem>
 *       <FormLabel>Email</FormLabel>
 *       <FormControl>
 *         <Input type="email" placeholder="user@example.com" {...field} />
 *       </FormControl>
 *       <FormMessage />
 *     </FormItem>
 *   )}
 * />
 * 
 * // After: 4 lines
 * <FormInput control={form.control} name="email" label="Email" type="email" placeholder="user@example.com" />
 * ```
 */
export function FormInput<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
    control,
    name,
    label,
    placeholder,
    description,
    disabled,
    type = 'text',
    className,
    autoComplete,
}: FormInputProps<TFieldValues, TName>) {
    return (
        <FormField
            control={control}
            name={name}
            render={({ field }) => (
                <FormItem className={className}>
                    <FormLabel>{label}</FormLabel>
                    <FormControl>
                        <Input
                            type={type}
                            placeholder={placeholder}
                            disabled={disabled}
                            autoComplete={autoComplete}
                            {...field}
                            value={field.value ?? ''}
                        />
                    </FormControl>
                    {description && <FormDescription>{description}</FormDescription>}
                    <FormMessage />
                </FormItem>
            )}
        />
    )
}
