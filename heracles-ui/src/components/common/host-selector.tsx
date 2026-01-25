/**
 * Host Selector Component
 *
 * Multi-select component for selecting system hostnames.
 * Fetches available hosts from the systems API.
 */

import { useState, useMemo } from 'react'
import { Check, ChevronsUpDown, X, Server, Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
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
import { useHostnames } from '@/hooks/use-systems'

interface HostSelectorProps {
  value: string[]
  onChange: (hosts: string[]) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function HostSelector({
  value = [],
  onChange,
  placeholder = 'Select hosts...',
  disabled = false,
  className,
}: HostSelectorProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const { data: hostnames, isLoading } = useHostnames()

  // Filter hostnames based on search
  const filteredHostnames = useMemo(() => {
    if (!hostnames) return []
    if (!searchQuery) return hostnames
    const query = searchQuery.toLowerCase()
    return hostnames.filter((h) => h.toLowerCase().includes(query))
  }, [hostnames, searchQuery])

  const handleSelect = (hostname: string) => {
    if (value.includes(hostname)) {
      onChange(value.filter((h) => h !== hostname))
    } else {
      onChange([...value, hostname])
    }
  }

  const handleRemove = (hostname: string) => {
    onChange(value.filter((h) => h !== hostname))
  }

  const handleClear = () => {
    onChange([])
  }

  return (
    <div className={cn('space-y-2', className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled || isLoading}
            className="w-full justify-between"
          >
            {isLoading ? (
              <span className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading hosts...
              </span>
            ) : value.length > 0 ? (
              <span className="truncate">
                {value.length} host{value.length !== 1 ? 's' : ''} selected
              </span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full min-w-[300px] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search hosts..."
              value={searchQuery}
              onValueChange={setSearchQuery}
            />
            <CommandList>
              <CommandEmpty>
                {isLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Loading...
                  </div>
                ) : hostnames?.length === 0 ? (
                  <div className="py-4 text-center text-sm">
                    <Server className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p>No systems found</p>
                    <p className="text-muted-foreground">
                      Create systems first to select them here
                    </p>
                  </div>
                ) : (
                  'No matching hosts found'
                )}
              </CommandEmpty>
              <CommandGroup>
                {filteredHostnames.map((hostname) => (
                  <CommandItem
                    key={hostname}
                    value={hostname}
                    onSelect={() => handleSelect(hostname)}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        value.includes(hostname) ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <Server className="mr-2 h-4 w-4 text-muted-foreground" />
                    {hostname}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Selected hosts as badges */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((hostname) => (
            <Badge
              key={hostname}
              variant="secondary"
              className="gap-1 pr-1"
            >
              <Server className="h-3 w-3" />
              {hostname}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-4 w-4 p-0 hover:bg-transparent"
                onClick={() => handleRemove(hostname)}
                disabled={disabled}
              >
                <X className="h-3 w-3" />
                <span className="sr-only">Remove {hostname}</span>
              </Button>
            </Badge>
          ))}
          {value.length > 1 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-muted-foreground"
              onClick={handleClear}
              disabled={disabled}
            >
              Clear all
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
