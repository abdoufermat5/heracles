/**
 * DHCP Options Editor Component
 *
 * A reusable component for editing DHCP options and statements
 * with autocomplete suggestions for common options.
 */

import { useState, useCallback } from 'react'
import { Plus, X, HelpCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
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

// Common DHCP options with descriptions
const COMMON_OPTIONS = [
  { name: 'routers', description: 'Default gateway IP address(es)', example: 'routers 192.168.1.1' },
  { name: 'domain-name-servers', description: 'DNS server IP address(es)', example: 'domain-name-servers 8.8.8.8, 8.8.4.4' },
  { name: 'domain-name', description: 'Domain name for DNS resolution', example: 'domain-name "example.com"' },
  { name: 'broadcast-address', description: 'Subnet broadcast address', example: 'broadcast-address 192.168.1.255' },
  { name: 'subnet-mask', description: 'Subnet mask', example: 'subnet-mask 255.255.255.0' },
  { name: 'ntp-servers', description: 'NTP server IP address(es)', example: 'ntp-servers 192.168.1.10' },
  { name: 'host-name', description: 'Client hostname', example: 'host-name "myhost"' },
  { name: 'log-servers', description: 'Syslog server IP address(es)', example: 'log-servers 192.168.1.20' },
  { name: 'time-servers', description: 'Time server IP address(es)', example: 'time-servers 192.168.1.10' },
  { name: 'netbios-name-servers', description: 'WINS server IP address(es)', example: 'netbios-name-servers 192.168.1.30' },
  { name: 'netbios-node-type', description: 'NetBIOS node type (1-8)', example: 'netbios-node-type 8' },
  { name: 'root-path', description: 'Path to client root filesystem', example: 'root-path "/nfs/root"' },
  { name: 'tftp-server-name', description: 'TFTP server hostname/IP', example: 'tftp-server-name "192.168.1.5"' },
  { name: 'bootfile-name', description: 'Boot file name for PXE', example: 'bootfile-name "pxelinux.0"' },
]

// Common DHCP statements with descriptions
const COMMON_STATEMENTS = [
  { name: 'default-lease-time', description: 'Default lease duration in seconds', example: 'default-lease-time 86400' },
  { name: 'max-lease-time', description: 'Maximum lease duration in seconds', example: 'max-lease-time 604800' },
  { name: 'min-lease-time', description: 'Minimum lease duration in seconds', example: 'min-lease-time 3600' },
  { name: 'authoritative', description: 'Server is authoritative for this network', example: 'authoritative' },
  { name: 'not authoritative', description: 'Server is not authoritative', example: 'not authoritative' },
  { name: 'ddns-update-style', description: 'Dynamic DNS update style', example: 'ddns-update-style interim' },
  { name: 'ddns-updates', description: 'Enable/disable DDNS updates', example: 'ddns-updates on' },
  { name: 'fixed-address', description: 'Fixed IP for host reservation', example: 'fixed-address 192.168.1.50' },
  { name: 'filename', description: 'Boot filename (PXE)', example: 'filename "pxelinux.0"' },
  { name: 'next-server', description: 'TFTP/boot server address', example: 'next-server 192.168.1.5' },
  { name: 'use-host-decl-names', description: 'Use host declarations for hostnames', example: 'use-host-decl-names on' },
  { name: 'deny', description: 'Deny clients (used in pools)', example: 'deny unknown-clients' },
  { name: 'allow', description: 'Allow clients (used in pools)', example: 'allow known-clients' },
  { name: 'ignore', description: 'Ignore clients', example: 'ignore bootp' },
]

interface DhcpOptionsEditorProps {
  type: 'options' | 'statements'
  value: string[]
  onChange: (value: string[]) => void
  disabled?: boolean
  className?: string
}

export function DhcpOptionsEditor({
  type,
  value,
  onChange,
  disabled = false,
  className,
}: DhcpOptionsEditorProps) {
  const [inputValue, setInputValue] = useState('')
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)

  const suggestions = type === 'options' ? COMMON_OPTIONS : COMMON_STATEMENTS

  const handleAdd = useCallback(() => {
    const trimmed = inputValue.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed])
      setInputValue('')
    }
  }, [inputValue, value, onChange])

  const handleRemove = useCallback(
    (index: number) => {
      onChange(value.filter((_, i) => i !== index))
    },
    [value, onChange]
  )

  const handleSelectSuggestion = useCallback(
    (suggestion: typeof suggestions[0]) => {
      setInputValue(suggestion.example)
      setIsPopoverOpen(false)
    },
    []
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        handleAdd()
      }
    },
    [handleAdd]
  )

  return (
    <div className={className}>
      {/* Current values */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {value.map((item, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="font-mono text-xs px-2 py-1"
            >
              {item}
              {!disabled && (
                <button
                  type="button"
                  onClick={() => handleRemove(index)}
                  className="ml-2 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}

      {/* Input with suggestions */}
      {!disabled && (
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Add ${type === 'options' ? 'option' : 'statement'}...`}
              className="font-mono text-sm pr-10"
            />
            <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                >
                  <HelpCircle className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="end">
                <Command>
                  <CommandInput placeholder={`Search ${type}...`} />
                  <CommandList>
                    <CommandEmpty>No {type} found.</CommandEmpty>
                    <CommandGroup heading={`Common ${type}`}>
                      {suggestions.map((suggestion) => (
                        <CommandItem
                          key={suggestion.name}
                          onSelect={() => handleSelectSuggestion(suggestion)}
                          className="flex flex-col items-start"
                        >
                          <span className="font-mono text-sm">{suggestion.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {suggestion.description}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <Button type="button" onClick={handleAdd} size="icon">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Help text */}
      {!disabled && (
        <p className="text-xs text-muted-foreground mt-2">
          Press Enter to add, or click the{' '}
          <HelpCircle className="h-3 w-3 inline" /> for suggestions
        </p>
      )}
    </div>
  )
}

// Quick reference component
export function DhcpOptionsReference() {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="sm">
            <HelpCircle className="h-4 w-4 mr-1" />
            DHCP Options Reference
          </Button>
        </TooltipTrigger>
        <TooltipContent className="w-96 p-4">
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Common Options</h4>
              <ul className="text-xs space-y-1">
                {COMMON_OPTIONS.slice(0, 5).map((opt) => (
                  <li key={opt.name}>
                    <code className="bg-muted px-1">{opt.name}</code> - {opt.description}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Common Statements</h4>
              <ul className="text-xs space-y-1">
                {COMMON_STATEMENTS.slice(0, 5).map((stmt) => (
                  <li key={stmt.name}>
                    <code className="bg-muted px-1">{stmt.name}</code> - {stmt.description}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
