/**
 * Sudo Role Access Control Tab
 *
 * Users, hosts, and run-as configuration for sudo role.
 */

import type { Control } from 'react-hook-form'
import { Users, Server } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
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
import type { SudoRoleData } from '@/types/sudo'

interface SudoRoleAccessTabProps {
  control: Control<any>
  role: SudoRoleData
}

export function SudoRoleAccessTab({ control, role }: SudoRoleAccessTabProps) {
  return (
    <div className="space-y-6">
      {/* Users & Groups Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Users & Groups
          </CardTitle>
          <CardDescription>Who can use this sudo role</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            control={control}
            name="sudoUser"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Sudo Users</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="user1, %groupname, ALL"
                    className="h-24 font-mono"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Comma-separated list of users or groups (%groupname). Use ALL
                  for everyone.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-muted-foreground mr-2">Current:</span>
            {role.sudoUser.map((user, i) => (
              <Badge key={i} variant="secondary">
                {user}
              </Badge>
            ))}
            {role.sudoUser.length === 0 && (
              <span className="text-xs text-muted-foreground">None</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Hosts Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            Hosts
          </CardTitle>
          <CardDescription>Where this sudo role applies</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            control={control}
            name="sudoHost"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Sudo Hosts</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="ALL, server1.example.com, 192.168.1.0/24"
                    className="h-20 font-mono"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Comma-separated hostnames, IP addresses, or CIDR ranges. Use
                  ALL for any host.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-muted-foreground mr-2">Current:</span>
            {role.sudoHost.map((host, i) => (
              <Badge key={i} variant="outline">
                {host}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Run As Card */}
      <Card>
        <CardHeader>
          <CardTitle>Run As</CardTitle>
          <CardDescription>
            Target user/group for command execution
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={control}
              name="sudoRunAsUser"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Run As User</FormLabel>
                  <FormControl>
                    <Input placeholder="ALL, root" {...field} />
                  </FormControl>
                  <FormDescription>
                    Target user(s) for sudo execution
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name="sudoRunAsGroup"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Run As Group</FormLabel>
                  <FormControl>
                    <Input placeholder="root, wheel" {...field} />
                  </FormControl>
                  <FormDescription>
                    Target group(s) for sudo execution
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
