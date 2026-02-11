import {
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
import type { Control, FieldPath, FieldValues } from 'react-hook-form'

export interface SelectOption {
    value: string
    label: string
    disabled?: boolean
}

export interface FormSelectProps<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> {
    control: Control<TFieldValues>
    name: TName
    label: string
    options: SelectOption[]
    placeholder?: string
    description?: string
    disabled?: boolean
    className?: string
    /** When set, prepends a "None" option that maps to empty string. */
    noneOption?: string
}

/**
 * Wrapper around FormField + Select that reduces boilerplate.
 * 
 * @example
 * ```tsx
 * <FormSelect
 *   control={form.control}
 *   name="status"
 *   label="Status"
 *   options={[
 *     { value: 'active', label: 'Active' },
 *     { value: 'inactive', label: 'Inactive' },
 *   ]}
 * />
 * ```
 */
export function FormSelect<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
    control,
    name,
    label,
    options,
    placeholder = 'Select an option',
    description,
    disabled,
    className,
    noneOption,
}: FormSelectProps<TFieldValues, TName>) {
    const SENTINEL = '__none__'
    return (
        <FormField
            control={control}
            name={name}
            render={({ field }) => (
                <FormItem className={className}>
                    <FormLabel>{label}</FormLabel>
                    <Select
                        onValueChange={(val) =>
                            field.onChange(noneOption && val === SENTINEL ? '' : val)
                        }
                        value={noneOption ? (field.value || SENTINEL) : field.value}
                        defaultValue={noneOption ? (field.value || SENTINEL) : field.value}
                        disabled={disabled}
                    >
                        <FormControl>
                            <SelectTrigger>
                                <SelectValue placeholder={placeholder} />
                            </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                            {noneOption && (
                                <SelectItem value={SENTINEL}>{noneOption}</SelectItem>
                            )}
                            {options.map((option) => (
                                <SelectItem
                                    key={option.value}
                                    value={option.value}
                                    disabled={option.disabled}
                                >
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    {description && <FormDescription>{description}</FormDescription>}
                    <FormMessage />
                </FormItem>
            )}
        />
    )
}
