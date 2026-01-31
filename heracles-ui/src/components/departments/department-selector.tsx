"use client"

import * as React from "react"
import { Building2, Check, ChevronsUpDown, Network } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { useDepartmentStore } from "@/stores"
import { useDepartmentTree } from "@/hooks"

export function DepartmentSelector() {
  const [open, setOpen] = React.useState(false)
  const {
    currentBase,
    setCurrentBase,
    flatList,
  } = useDepartmentStore()

  // Fetch the department tree on mount to populate flatList
  useDepartmentTree()

  // Flatten tree with depth indicator for display
  const getDisplayItems = () => {
    return flatList.map(dept => ({
      value: dept.dn,
      label: dept.ou,
      path: dept.path,
      depth: dept.depth
    }))
  }

  const items = getDisplayItems()
  const selectedLabel = currentBase
    ? flatList.find(d => d.dn === currentBase)?.ou
    : "/"

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          size="sm"
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {currentBase ? (
              <Network className="h-4 w-4 shrink-0 opacity-50" />
            ) : (
              <Building2 className="h-4 w-4 shrink-0 opacity-50" />
            )}
            <span className="truncate text-sm">{selectedLabel}</span>
          </div>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search department..." />
          <CommandList>
            <CommandEmpty>No department found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="all"
                onSelect={() => {
                  setCurrentBase(null)
                  setOpen(false)
                }}
                className="gap-2"
              >
                <Building2 className="mr-2 h-4 w-4 text-muted-foreground" />
                <span className="font-mono">/</span>
                {!currentBase && <Check className="ml-auto h-4 w-4" />}
              </CommandItem>
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Departments">
              {items.map((framework) => (
                <CommandItem
                  key={framework.value}
                  value={framework.label} // Use label for search match
                  onSelect={() => {
                    setCurrentBase(framework.value, framework.path)
                    setOpen(false)
                  }}
                  className="gap-2"
                >
                  <div
                    className="flex items-center gap-2"
                    style={{ paddingLeft: `${framework.depth * 12}px` }}
                  >
                    <Network className="h-4 w-4 text-muted-foreground" />
                    <span>{framework.label}</span>
                  </div>
                  {currentBase === framework.value && (
                    <Check className="ml-auto h-4 w-4" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
