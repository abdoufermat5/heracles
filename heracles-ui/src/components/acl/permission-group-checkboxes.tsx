/**
 * Permission Group Checkboxes Component
 *
 * Renders all registered permissions grouped by scope as checkboxes.
 * Used in the policy create/edit form.
 */

import { useMemo } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/common'
import { useAclPermissions } from '@/hooks'
import type { AclPermission } from '@/types/acl'

interface PermissionGroupCheckboxesProps {
  selected: string[]
  onChange: (permissions: string[]) => void
  disabled?: boolean
}

export function PermissionGroupCheckboxes({
  selected,
  onChange,
  disabled = false,
}: PermissionGroupCheckboxesProps) {
  const { data: permissions, isLoading } = useAclPermissions()

  // Group permissions by scope
  const grouped = useMemo(() => {
    if (!permissions) return new Map<string, AclPermission[]>()
    const map = new Map<string, AclPermission[]>()
    for (const perm of permissions) {
      const existing = map.get(perm.scope) || []
      existing.push(perm)
      map.set(perm.scope, existing)
    }
    return map
  }, [permissions])

  const handleToggle = (permName: string, checked: boolean) => {
    if (checked) {
      onChange([...selected, permName])
    } else {
      onChange(selected.filter((p) => p !== permName))
    }
  }

  const handleToggleScope = (scope: string, checked: boolean) => {
    const scopePerms = grouped.get(scope)?.map((p) => p.name) ?? []
    if (checked) {
      const newSelected = new Set([...selected, ...scopePerms])
      onChange(Array.from(newSelected))
    } else {
      onChange(selected.filter((p) => !scopePerms.includes(p)))
    }
  }

  const isScopeFullySelected = (scope: string) => {
    const scopePerms = grouped.get(scope)?.map((p) => p.name) ?? []
    return scopePerms.every((p) => selected.includes(p))
  }

  const isScopePartiallySelected = (scope: string) => {
    const scopePerms = grouped.get(scope)?.map((p) => p.name) ?? []
    const selectedCount = scopePerms.filter((p) => selected.includes(p)).length
    return selectedCount > 0 && selectedCount < scopePerms.length
  }

  if (isLoading) {
    return <LoadingSpinner />
  }

  const scopeLabels: Record<string, string> = {
    user: 'Users',
    group: 'Groups',
    role: 'Roles',
    department: 'Departments',
    config: 'Configuration',
    acl: 'Access Control',
    audit: 'Audit',
    posix: 'POSIX',
    sudo: 'Sudo',
    ssh: 'SSH Keys',
    dns: 'DNS',
    dhcp: 'DHCP',
    mail: 'Mail',
    systems: 'Systems',
  }

  const scopeOrder = ['user', 'group', 'role', 'department', 'config', 'acl', 'audit']

  // Sort: core scopes first in defined order, then plugin scopes alphabetically
  const sortedScopes = Array.from(grouped.keys()).sort((a, b) => {
    const aIdx = scopeOrder.indexOf(a)
    const bIdx = scopeOrder.indexOf(b)
    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx
    if (aIdx !== -1) return -1
    if (bIdx !== -1) return 1
    return a.localeCompare(b)
  })

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {sortedScopes.map((scope) => {
        const scopePerms = grouped.get(scope) ?? []
        const fullySelected = isScopeFullySelected(scope)
        const partiallySelected = isScopePartiallySelected(scope)
        const selectedCount = scopePerms.filter((p) => selected.includes(p.name)).length

        return (
          <Card key={scope} className="overflow-hidden">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`scope-${scope}`}
                    checked={fullySelected}
                    // Use data attribute for indeterminate styling
                    data-indeterminate={partiallySelected && !fullySelected}
                    onCheckedChange={(checked) => handleToggleScope(scope, !!checked)}
                    disabled={disabled}
                  />
                  <CardTitle className="text-sm font-semibold">
                    <Label htmlFor={`scope-${scope}`} className="cursor-pointer">
                      {scopeLabels[scope] || scope.charAt(0).toUpperCase() + scope.slice(1)}
                    </Label>
                  </CardTitle>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {selectedCount}/{scopePerms.length}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-2">
                {scopePerms.map((perm) => (
                  <div key={perm.name} className="flex items-start gap-2">
                    <Checkbox
                      id={`perm-${perm.name}`}
                      checked={selected.includes(perm.name)}
                      onCheckedChange={(checked) => handleToggle(perm.name, !!checked)}
                      disabled={disabled}
                    />
                    <div className="grid gap-0.5 leading-none">
                      <Label
                        htmlFor={`perm-${perm.name}`}
                        className="cursor-pointer text-sm font-medium"
                      >
                        {perm.action}
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        {perm.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
