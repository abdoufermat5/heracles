/**
 * App Header Component
 *
 * Top navigation bar with breadcrumbs, global search, and user controls.
 */

import { useState, useEffect, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
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
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { useAuthStore } from '@/stores'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'
import { CommandPalette } from '@/components/layout/command-palette'

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


function getBreadcrumbs(pathname: string) {
  if (pathname.startsWith(PLUGIN_ROUTES.DHCP.SERVICES)) {
    const parts = pathname.split('/').filter(Boolean)
    const breadcrumbs: { label: string; href?: string }[] = [
      { label: 'DHCP', href: PLUGIN_ROUTES.DHCP.SERVICES },
    ]

    if (parts.length >= 2) {
      const serviceCn = decodeURIComponent(parts[1])
      breadcrumbs.push({
        label: serviceCn,
        href: PLUGIN_ROUTES.DHCP.SERVICE_DETAIL.replace(':serviceCn', serviceCn),
      })
    }

    if (parts.includes('subnets')) {
      const subnetIndex = parts.indexOf('subnets') + 1
      const subnetCn = parts[subnetIndex]
      if (subnetCn) {
        breadcrumbs.push({
          label: decodeURIComponent(subnetCn),
          href: PLUGIN_ROUTES.DHCP.SUBNET_DETAIL
            .replace(':serviceCn', decodeURIComponent(parts[1]))
            .replace(':subnetCn', decodeURIComponent(subnetCn)),
        })
      }
    }

    if (parts.includes('hosts')) {
      const hostIndex = parts.indexOf('hosts') + 1
      const hostCn = parts[hostIndex]
      if (hostCn) {
        breadcrumbs.push({
          label: decodeURIComponent(hostCn),
          href: PLUGIN_ROUTES.DHCP.HOST_DETAIL
            .replace(':serviceCn', decodeURIComponent(parts[1]))
            .replace(':hostCn', decodeURIComponent(hostCn)),
        })
      }
    }

    return breadcrumbs
  }

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
  const { user, logout } = useAuthStore()
  const [isDark, setIsDark] = useState(
    () => document.documentElement.classList.contains('dark')
  )
  const [searchOpen, setSearchOpen] = useState(false)

  const breadcrumbs = getBreadcrumbs(location.pathname)

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
        <div className="hidden lg:flex items-center gap-2">
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

      <CommandPalette open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  )
}
