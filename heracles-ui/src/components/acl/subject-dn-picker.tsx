/**
 * Subject DN Picker Component
 *
 * Searchable dropdown for picking user/group/role DNs when creating assignments.
 * Fetches from the respective APIs based on the selected subject type.
 * 
 * Department-aware: Only shows users/groups from the currently selected department.
 */

import { useState, useMemo, useEffect } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useUsers, useGroups } from '@/hooks'
import { useDepartmentStore } from '@/stores/department-store'
import type { User, Group } from '@/types'

interface SubjectDnPickerProps {
  subjectType: 'user' | 'group' | 'role'
  value: string
  onChange: (dn: string) => void
  disabled?: boolean
}

export function SubjectDnPicker({
  subjectType,
  value,
  onChange,
  disabled = false,
}: SubjectDnPickerProps) {
  const [open, setOpen] = useState(false)
  
  // Get current department context for filtering
  const currentDepartment = useDepartmentStore((state) => state.currentBase)

  // Clear selection when department changes
  useEffect(() => {
    if (value) {
      onChange('')
    }
  }, [currentDepartment])

  // Fetch users/groups based on subject type, scoped to current department
  const { data: usersData } = useUsers({ 
    page_size: 200,
    base: currentDepartment || undefined,
  })
  const { data: groupsData } = useGroups({ 
    page_size: 200,
    base: currentDepartment || undefined,
  })

  const items = useMemo(() => {
    if (subjectType === 'user') {
      return (usersData?.users ?? []).map((u: User) => ({
        dn: u.dn,
        label: `${u.uid} — ${u.displayName || u.cn || ''}`,
        shortLabel: u.uid,
      }))
    }
    if (subjectType === 'group') {
      return (groupsData?.groups ?? []).map((g: Group) => ({
        dn: g.dn,
        label: `${g.cn}${g.description ? ` — ${g.description}` : ''}`,
        shortLabel: g.cn,
      }))
    }
    if (subjectType === 'role') {
      // Roles use the same groups API with a type filter, or we show groups
      // For now, allow free-text entry for roles
      return (groupsData?.groups ?? []).map((g: Group) => ({
        dn: g.dn,
        label: `${g.cn}${g.description ? ` — ${g.description}` : ''}`,
        shortLabel: g.cn,
      }))
    }
    return []
  }, [subjectType, usersData, groupsData])

  const selectedItem = items.find((i) => i.dn === value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          <span className="truncate">
            {selectedItem ? selectedItem.label : value || 'Select subject...'}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder={`Search ${subjectType}s...`} />
          <CommandList>
            <CommandEmpty>No {subjectType}s found.</CommandEmpty>
            <CommandGroup>
              {items.map((item) => (
                <CommandItem
                  key={item.dn}
                  value={item.label}
                  onSelect={() => {
                    onChange(item.dn)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      'mr-2 h-4 w-4',
                      value === item.dn ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <span className="truncate">{item.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
