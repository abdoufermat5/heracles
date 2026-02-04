import { Link, useLocation } from 'react-router-dom'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  LayoutDashboard,
  Users,
  UsersRound,
  Server,
  Settings,
  LogOut,
  ChevronUp,
  ShieldCheck,
  Globe,
  Network,
  Building2,
  KeyRound,
} from 'lucide-react'
import { useAuthStore, usePluginStore, PLUGIN_NAMES } from '@/stores'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'
import { DepartmentSelector } from '@/components/departments'

// Main navigation - Core identity management
const coreNavItems = [
  {
    title: 'Dashboard',
    url: ROUTES.DASHBOARD,
    icon: LayoutDashboard,
  },
  {
    title: 'Users',
    url: ROUTES.USERS,
    icon: Users,
  },
  {
    title: 'Groups',
    url: ROUTES.GROUPS,
    icon: UsersRound,
  },
  {
    title: 'Departments',
    url: ROUTES.DEPARTMENTS,
    icon: Building2,
  },
]

// Infrastructure - Systems & Network
const infrastructureNavItems = [
  {
    title: 'Systems',
    url: PLUGIN_ROUTES.SYSTEMS.LIST,
    icon: Server,
    pluginName: PLUGIN_NAMES.SYSTEMS,
  },
  {
    title: 'DNS Zones',
    url: PLUGIN_ROUTES.DNS.ZONES,
    icon: Globe,
    pluginName: PLUGIN_NAMES.DNS,
  },
  {
    title: 'DHCP',
    url: PLUGIN_ROUTES.DHCP.SERVICES,
    icon: Network,
    pluginName: PLUGIN_NAMES.DHCP,
  },
]

// Security & Access Control
const securityNavItems = [
  {
    title: 'Sudo Roles',
    url: PLUGIN_ROUTES.SUDO.ROLES,
    icon: ShieldCheck,
    pluginName: PLUGIN_NAMES.SUDO,
  },
  {
    title: 'SSH Keys',
    url: '/ssh-keys',  // TODO: Add to routes when SSH management page is ready
    icon: KeyRound,
    disabled: true,
    pluginName: PLUGIN_NAMES.SSH,
  },
]

// Communication - Mail (future)
// const communicationNavItems = [
//   {
//     title: 'Mail Accounts',
//     url: '/mail',
//     icon: Mail,
//   },
// ]

export function AppSidebar() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const plugins = usePluginStore((state) => state.plugins)
  const isInitialized = usePluginStore((state) => state.isInitialized)
  
  // Helper to check if plugin is enabled
  const isPluginEnabled = (name: string) => {
    // If plugins haven't loaded yet, show all by default
    if (!isInitialized || !plugins || plugins.length === 0) return true
    const plugin = plugins.find((p) => p.name === name)
    // If plugin not found in list, default to true (graceful degradation)
    if (!plugin) return true
    return plugin.enabled
  }

  // Filter nav items based on plugin enabled state
  const filteredInfrastructureItems = infrastructureNavItems.filter(
    (item) => !item.pluginName || isPluginEnabled(item.pluginName)
  )
  const filteredSecurityItems = securityNavItems.filter(
    (item) => !item.pluginName || isPluginEnabled(item.pluginName)
  )

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
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-2">
          <img src="/logo-icon.png" alt="Logo" className="h-8 w-8 object-contain" />
          <div className="flex flex-col">
            <span className="text-lg font-bold">Heracles</span>
            <span className="text-xs text-muted-foreground">Identity Management</span>
          </div>
        </div>
        <div className="px-2 pb-2 overflow-hidden">
          <DepartmentSelector />
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* Core Identity Management */}
        <SidebarGroup>
          <SidebarGroupLabel>Identity</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {coreNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === item.url || location.pathname.startsWith(item.url + '/')}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Infrastructure */}
        {filteredInfrastructureItems.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel>Infrastructure</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {filteredInfrastructureItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={location.pathname === item.url || location.pathname.startsWith(item.url + '/')}
                    >
                      <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Security & Access */}
        {filteredSecurityItems.length > 0 && (
          <SidebarGroup>
            <SidebarGroupLabel>Security</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {filteredSecurityItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={location.pathname === item.url || location.pathname.startsWith(item.url + '/')}
                      disabled={'disabled' in item && item.disabled}
                      className={'disabled' in item && item.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                    >
                      {'disabled' in item && item.disabled ? (
                        <span className="flex items-center gap-2">
                          <item.icon />
                          <span>{item.title}</span>
                        </span>
                    ) : (
                      <Link to={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    )}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        <SidebarSeparator />

        {/* Administration */}
        <SidebarGroup>
          <SidebarGroupLabel>Administration</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={location.pathname === ROUTES.SETTINGS || location.pathname.startsWith(ROUTES.SETTINGS + '/')}
                >
                  <Link to={ROUTES.SETTINGS}>
                    <Settings />
                    <span>Settings</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>{getInitials(user?.displayName || user?.cn)}</AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{user?.displayName || user?.cn}</span>
                    <span className="truncate text-xs text-muted-foreground">{user?.mail || user?.uid}</span>
                  </div>
                  <ChevronUp className="ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
                side="top"
                align="start"
                sideOffset={4}
              >
                <DropdownMenuItem asChild>
                  <Link to={ROUTES.SETTINGS}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
