/**
 * Sudo Role Options Tab
 *
 * Sudo options configuration for sudo role.
 */

import type { Control } from 'react-hook-form'
import { Shield } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { FormField, FormItem, FormMessage } from '@/components/ui/form'
import { SUDO_OPTIONS } from '@/types/sudo'
import type { SudoRoleData } from '@/types/sudo'

interface SudoRoleOptionsTabProps {
  control: Control<any>
  role: SudoRoleData
}

export function SudoRoleOptionsTab({ control, role }: SudoRoleOptionsTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Sudo Options
        </CardTitle>
        <CardDescription>
          Configure sudo behavior for this role
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FormField
          control={control}
          name="sudoOption"
          render={({ field }) => (
            <FormItem>
              <div className="grid grid-cols-2 gap-4">
                {SUDO_OPTIONS.map((option) => (
                  <div
                    key={option.value}
                    className="flex items-start space-x-3 p-3 rounded-lg border hover:bg-accent/50"
                  >
                    <Checkbox
                      id={option.value}
                      checked={field.value?.includes(option.value)}
                      onCheckedChange={(checked) => {
                        const current = field.value || []
                        if (checked) {
                          field.onChange([...current, option.value])
                        } else {
                          field.onChange(current.filter((v: string) => v !== option.value))
                        }
                      }}
                    />
                    <div className="grid gap-1 leading-none">
                      <label
                        htmlFor={option.value}
                        className="text-sm font-medium cursor-pointer"
                      >
                        {option.label}
                      </label>
                      <p className="text-xs text-muted-foreground">
                        {option.description}
                      </p>
                      <code className="text-xs bg-muted px-1 rounded">
                        {option.value}
                      </code>
                    </div>
                  </div>
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <Separator className="my-4" />

        <div className="space-y-2">
          <span className="text-sm font-medium">Active Options:</span>
          <div className="flex flex-wrap gap-2">
            {role.sudoOption.map((opt, i) => (
              <Badge key={i} variant="secondary">
                {opt}
              </Badge>
            ))}
            {role.sudoOption.length === 0 && (
              <span className="text-muted-foreground">No options configured</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
