import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'
import {
  Home,
  Users,
  UsersRound,
  ShieldCheck,
  Server,
  Settings,
  Clock,
} from 'lucide-react'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'
import { useCommandSearch } from '@/hooks'
import { useRecentStore } from '@/stores'

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const navigationItems = [
  { label: 'Dashboard', href: ROUTES.DASHBOARD, icon: Home, shortcut: 'D' },
  { label: 'Users', href: ROUTES.USERS, icon: Users, shortcut: 'U' },
  { label: 'Groups & Roles', href: ROUTES.GROUPS, icon: UsersRound, shortcut: 'G' },
  { label: 'Sudo Roles', href: PLUGIN_ROUTES.SUDO.ROLES, icon: ShieldCheck, shortcut: 'S' },
  { label: 'Systems', href: PLUGIN_ROUTES.SYSTEMS.LIST, icon: Server, shortcut: 'Y' },
  { label: 'Settings', href: ROUTES.SETTINGS, icon: Settings, shortcut: ',' },
]

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const { users, groups, isLoading } = useCommandSearch(query)
  const recentItems = useRecentStore((state) => state.items)

  const hasQuery = query.trim().length > 0
  const showSearchResults = query.trim().length >= 2

  const handleSelect = (href: string) => {
    onOpenChange(false)
    setQuery('')
    navigate(href)
  }

  const recent = useMemo(() => recentItems.slice(0, 10), [recentItems])

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Search">
      <CommandInput
        placeholder="Search users, groups, and pages..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>
          {isLoading ? 'Searching...' : 'No results found.'}
        </CommandEmpty>

        {!hasQuery && recent.length > 0 && (
          <>
            <CommandGroup heading="Recent">
              {recent.map((item) => (
                <CommandItem
                  key={item.href}
                  value={`${item.label} ${item.description ?? ''}`.trim()}
                  onSelect={() => handleSelect(item.href)}
                >
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.description && (
                    <span className="text-xs text-muted-foreground truncate">
                      {item.description}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        <CommandGroup heading="Navigation">
          {navigationItems.map((item) => (
            <CommandItem
              key={item.href}
              value={item.label}
              onSelect={() => handleSelect(item.href)}
            >
              <item.icon className="h-4 w-4 text-muted-foreground" />
              <span>{item.label}</span>
              <CommandShortcut>{item.shortcut}</CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>

        {showSearchResults && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Users">
              {users.map((user) => (
                <CommandItem
                  key={user.uid}
                  value={`${user.uid} ${user.displayName ?? ''} ${user.mail ?? ''}`.trim()}
                  onSelect={() =>
                    handleSelect(ROUTES.USER_DETAIL.replace(':uid', user.uid))
                  }
                >
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{user.uid}</span>
                  {user.displayName && (
                    <span className="text-xs text-muted-foreground truncate">
                      {user.displayName}
                    </span>
                  )}
                </CommandItem>
              ))}
              {!isLoading && users.length === 0 && (
                <CommandItem disabled>No matching users</CommandItem>
              )}
            </CommandGroup>
            <CommandGroup heading="Groups">
              {groups.map((group) => (
                <CommandItem
                  key={group.cn}
                  value={`${group.cn} ${group.description ?? ''}`.trim()}
                  onSelect={() =>
                    handleSelect(ROUTES.GROUP_DETAIL.replace(':cn', group.cn))
                  }
                >
                  <UsersRound className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{group.cn}</span>
                  {group.description && (
                    <span className="text-xs text-muted-foreground truncate">
                      {group.description}
                    </span>
                  )}
                </CommandItem>
              ))}
              {!isLoading && groups.length === 0 && (
                <CommandItem disabled>No matching groups</CommandItem>
              )}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  )
}
