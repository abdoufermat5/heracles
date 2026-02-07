import {
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
} from '@/components/ui/form'
import { Switch } from '@/components/ui/switch'
import type { Control, FieldPath, FieldValues } from 'react-hook-form'

export interface FormSwitchProps<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> {
    control: Control<TFieldValues>
    name: TName
    label: string
    description?: string
    disabled?: boolean
    className?: string
}

/**
 * Wrapper around FormField + Switch that reduces boilerplate.
 */
export function FormSwitch<
    TFieldValues extends FieldValues = FieldValues,
    TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
    control,
    name,
    label,
    description,
    disabled,
    className,
}: FormSwitchProps<TFieldValues, TName>) {
    return (
        <FormField
            control={control}
            name={name}
            render={({ field }) => (
                <FormItem className={`flex flex-row items-center justify-between rounded-lg border p-4 ${className ?? ''}`}>
                    <div className="space-y-0.5">
                        <FormLabel className="text-base">{label}</FormLabel>
                        {description && <FormDescription>{description}</FormDescription>}
                    </div>
                    <FormControl>
                        <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                            disabled={disabled}
                        />
                    </FormControl>
                </FormItem>
            )}
        />
    )
}
