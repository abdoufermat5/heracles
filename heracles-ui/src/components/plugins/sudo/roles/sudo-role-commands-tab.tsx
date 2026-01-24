/**
 * Sudo Role Commands Tab
 *
 * Allowed commands configuration for sudo role.
 */

import type { UseFormReturn } from 'react-hook-form'
import { Terminal } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { COMMON_COMMANDS } from '@/types/sudo'
import type { SudoRoleData } from '@/types/sudo'

interface SudoRoleCommandsTabProps {
  form: UseFormReturn<any>
  role: SudoRoleData
}

export function SudoRoleCommandsTab({ form, role }: SudoRoleCommandsTabProps) {
  const handleQuickAddCommand = (commandValue: string) => {
    const current = form.getValues('sudoCommand') || ''
    const newValue = current ? `${current}, ${commandValue}` : commandValue
    form.setValue('sudoCommand', newValue, { shouldDirty: true })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Terminal className="h-5 w-5" />
          Allowed Commands
        </CardTitle>
        <CardDescription>
          Commands this role can execute with sudo
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormField
          control={form.control}
          name="sudoCommand"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Commands</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="ALL, /usr/bin/systemctl restart nginx, !/bin/su"
                  className="h-32 font-mono"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Comma-separated list of commands with full paths. Use ! prefix
                to deny. ALL allows everything.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="space-y-2">
          <span className="text-sm font-medium">Quick Add Commands:</span>
          <div className="flex flex-wrap gap-2">
            {COMMON_COMMANDS.map((cmd) => (
              <Badge
                key={cmd.value}
                variant="outline"
                className="cursor-pointer hover:bg-accent"
                onClick={() => handleQuickAddCommand(cmd.value)}
              >
                {cmd.label}
              </Badge>
            ))}
          </div>
        </div>

        <Separator />

        <div className="space-y-2">
          <span className="text-sm font-medium">Current Commands:</span>
          <div className="flex flex-wrap gap-2">
            {role.sudoCommand.map((cmd, i) => (
              <Badge
                key={i}
                variant={
                  cmd === 'ALL'
                    ? 'destructive'
                    : cmd.startsWith('!')
                      ? 'outline'
                      : 'default'
                }
              >
                {cmd}
              </Badge>
            ))}
            {role.sudoCommand.length === 0 && (
              <span className="text-muted-foreground">No commands specified</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
