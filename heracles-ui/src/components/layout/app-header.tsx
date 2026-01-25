/**
 * App Header Component
 *
 * Top navigation bar with breadcrumbs, global search, and user controls.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Search,
  Bell,
  MoonStar,
  SunMedium,
  ChevronRight,
  Home,
  Users,
  UsersRound,
  ShieldCheck,
  Server,
  Settings,
  LogOut,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { useAuthStore } from '@/stores'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'

// Breadcrumb configuration based on routes
const routeBreadcrumbs: Record<string, { label: string; icon?: React.ElementType }> = {
  '/': { label: 'Dashboard', icon: Home },
  '/users': { label: 'Users', icon: Users },
  '/groups': { label: 'Groups', icon: UsersRound },
  '/systems': { label: 'Systems', icon: Server },
  '/settings': { label: 'Settings', icon: Settings },
  '/sudo/roles': { label: 'Sudo Roles', icon: ShieldCheck },
  '/posix/groups': { label: 'POSIX Groups', icon: UsersRound },
  '/posix/mixed-groups': { label: 'Mixed Groups', icon: UsersRound },
}

// Quick search items
const searchItems = [
  { label: 'Users', href: ROUTES.USERS, icon: Users, shortcut: 'U' },
  { label: 'Groups', href: ROUTES.GROUPS, icon: UsersRound, shortcut: 'G' },
  { label: 'Sudo Roles', href: PLUGIN_ROUTES.SUDO.ROLES, icon: ShieldCheck, shortcut: 'S' },
  { label: 'Systems', href: PLUGIN_ROUTES.SYSTEMS.LIST, icon: Server, shortcut: 'Y' },
  { label: 'Settings', href: ROUTES.SETTINGS, icon: Settings, shortcut: ',' },
]

function getBreadcrumbs(pathname: string) {
  const parts = pathname.split('/').filter(Boolean)
  const breadcrumbs: { label: string; href?: string }[] = []

  let currentPath = ''
  for (let i = 0; i < parts.length; i++) {
    currentPath += '/' + parts[i]
    const config = routeBreadcrumbs[currentPath]

    if (config) {
      breadcrumbs.push({
        label: config.label,
        href: i < parts.length - 1 ? currentPath : undefined,
      })
    } else {
      // Handle dynamic segments (e.g., user/:uid)
      const label = decodeURIComponent(parts[i])
      breadcrumbs.push({
        label: label.charAt(0).toUpperCase() + label.slice(1),
        href: i < parts.length - 1 ? currentPath : undefined,
      })
    }
  }

  return breadcrumbs
}

export function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [isDark, setIsDark] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const breadcrumbs = getBreadcrumbs(location.pathname)

  // Theme toggle
  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains('dark')
    setIsDark(isDarkMode)
  }, [])

  const toggleTheme = useCallback(() => {
    const newIsDark = !isDark
    setIsDark(newIsDark)
    document.documentElement.classList.toggle('dark', newIsDark)
    localStorage.setItem('theme', newIsDark ? 'dark' : 'light')
  }, [isDark])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Open search with Cmd/Ctrl + K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Handle search navigation
  const handleSearchSelect = (href: string) => {
    setSearchOpen(false)
    setSearchQuery('')
    navigate(href)
  }

  const filteredSearchItems = searchQuery
    ? searchItems.filter((item) =>
        item.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : searchItems

  const getInitials = (name?: string) => {
    if (!name) return 'U'
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <>
      <header className="flex h-14 shrink-0 items-center gap-2 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
        {/* Left: Sidebar trigger + Breadcrumbs */}
        <div className="flex items-center gap-2 flex-1">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4" />

          {/* Breadcrumbs */}
          <nav className="hidden md:flex items-center gap-1 text-sm">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link
                    to="/"
                    className="flex items-center text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Home className="h-4 w-4" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent>Dashboard</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            {breadcrumbs.map((item, index) => (
              <div key={index} className="flex items-center gap-1">
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                {item.href ? (
                  <Link
                    to={item.href}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span className="font-medium text-foreground">{item.label}</span>
                )}
              </div>
            ))}
          </nav>
        </div>

        {/* Center: Search */}
        <div className="hidden lg:flex items-center">
          <Button
            variant="outline"
            className="relative h-9 w-64 justify-start text-sm text-muted-foreground"
            onClick={() => setSearchOpen(true)}
          >
            <Search className="mr-2 h-4 w-4" />
            <span>Search...</span>
            <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          {/* Mobile search button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="lg:hidden h-9 w-9"
                  onClick={() => setSearchOpen(true)}
                >
                  <Search className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Search (⌘K)</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Notifications */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="h-9 w-9 relative">
                  <Bell className="h-4 w-4" />
                  {/* Notification badge - uncomment when notifications are implemented
                  <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-destructive" />
                  */}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Notifications</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Theme toggle */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9"
                  onClick={toggleTheme}
                >
                  {isDark ? (
                    <SunMedium className="h-4 w-4" />
                  ) : (
                    <MoonStar className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isDark ? 'Light mode' : 'Dark mode'}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <Separator orientation="vertical" className="h-6 mx-2" />

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-9 gap-2 px-2">
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="text-xs">
                    {getInitials(user?.displayName || user?.cn)}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden md:block text-sm font-medium max-w-[100px] truncate">
                  {user?.displayName || user?.cn || 'User'}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium">{user?.displayName || user?.cn}</p>
                  <p className="text-xs text-muted-foreground">{user?.mail || user?.uid}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to={ROUTES.SETTINGS}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                  <DropdownMenuShortcut>⌘,</DropdownMenuShortcut>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => logout()} className="text-destructive focus:text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Command palette / Search dialog */}
      <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
        <DialogContent className="overflow-hidden p-0 shadow-lg">
          <DialogHeader className="sr-only">
            <DialogTitle>Search</DialogTitle>
          </DialogHeader>
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Input
              placeholder="Search navigation..."
              className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
          </div>
          <div className="max-h-[300px] overflow-y-auto p-2">
            {filteredSearchItems.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No results found.
              </p>
            ) : (
              <div className="space-y-1">
                <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                  Navigation
                </p>
                {filteredSearchItems.map((item) => (
                  <button
                    key={item.href}
                    onClick={() => handleSearchSelect(item.href)}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <item.icon className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1 text-left">{item.label}</span>
                    <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                      {item.shortcut}
                    </kbd>
                  </button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
