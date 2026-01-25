/**
 * Trust Mode Section Component
 *
 * Reusable form section for configuring system trust settings.
 * Used in POSIX groups, mixed groups, and user forms.
 */

import type { Control, FieldValues, Path } from 'react-hook-form'
import { useWatch } from 'react-hook-form'
import { Badge } from '@/components/ui/badge'
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
import { HostSelector } from '../host-selector'
import type { TrustMode } from '@/types/posix'

interface TrustModeSectionProps<T extends FieldValues> {
  /** react-hook-form control object */
  control: Control<T>
  /** Field name for trustMode (default: 'trustMode') */
  trustModeFieldName?: Path<T>
  /** Field name for host array (default: 'host') */
  hostFieldName?: Path<T>
  /** Current trust mode value (for displaying badge in edit mode) */
  currentTrustMode?: TrustMode | null
  /** Title for the section */
  title?: string
  /** Whether this section is optional (affects title) */
  optional?: boolean
}

export function TrustModeSection<T extends FieldValues>({
  control,
  trustModeFieldName = 'trustMode' as Path<T>,
  hostFieldName = 'host' as Path<T>,
  currentTrustMode,
  title = 'System Trust',
  optional = false,
}: TrustModeSectionProps<T>) {
  // Watch the trustMode field to conditionally show host input
  const trustMode = useWatch({
    control,
    name: trustModeFieldName,
  })

  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm">
          {title}
          {optional && ' (Optional)'}
        </h4>
        {currentTrustMode && (
          <Badge
            variant={currentTrustMode === 'fullaccess' ? 'default' : 'secondary'}
          >
            {currentTrustMode === 'fullaccess' ? 'Full Access' : 'By Host'}
          </Badge>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Control which systems this group has access to
      </p>

      <FormField
        control={control}
        name={trustModeFieldName}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Trust Mode</FormLabel>
            <Select
              onValueChange={(value) =>
                field.onChange(value === 'none' ? null : value)
              }
              value={(field.value as string) ?? 'none'}
            >
              <FormControl>
                <SelectTrigger>
                  <SelectValue placeholder="No restriction" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="none">No restriction</SelectItem>
                <SelectItem value="fullaccess">
                  Full access (all systems)
                </SelectItem>
                <SelectItem value="byhost">Restricted by host</SelectItem>
              </SelectContent>
            </Select>
            <FormDescription>
              {!trustMode && 'Group will have default system access'}
              {trustMode === 'fullaccess' && 'Group can access all systems'}
              {trustMode === 'byhost' && 'Group can only access specified hosts'}
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {trustMode === 'byhost' && (
        <FormField
          control={control}
          name={hostFieldName}
          render={({ field }) => (
            <FormItem>
              <FormLabel>Allowed Hosts *</FormLabel>
              <FormControl>
                <HostSelector
                  value={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                  placeholder="Select allowed hosts..."
                />
              </FormControl>
              <FormDescription>
                Select the systems this group can access
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      )}
    </div>
  )
}
