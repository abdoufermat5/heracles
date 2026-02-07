import { Link } from 'react-router-dom'
import { Users, UsersRound, Activity, TrendingUp, UserPlus, ChevronDown, Terminal, Layers, Shield, Building2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { PageHeader, CardSkeleton, ErrorDisplay } from '@/components/common'
import { useHealth, useStats } from '@/hooks'
import { useAuthStore, useDepartmentStore } from '@/stores'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'

export function DashboardPage() {
  const { user } = useAuthStore()
  const { currentBase, currentPath } = useDepartmentStore()
  const { data: statsData, isLoading: statsLoading, error: statsError } = useStats()
  const { data: healthData, isLoading: healthLoading, error: healthError } = useHealth()

  if (statsLoading || healthLoading) {
    return (
      <div>
        <PageHeader
          title={`Welcome, ${user?.displayName || user?.cn || 'User'}`}
          description="Here's an overview of your identity management system"
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
          {Array.from({ length: 4 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <CardSkeleton key={index} contentLines={2} />
          ))}
        </div>
      </div>
    )
  }

  if (statsError || healthError) {
    return (
      <ErrorDisplay
        message={(statsError || healthError)?.message || 'Failed to load dashboard data'}
      />
    )
  }

  // Determine context label
  const contextLabel = currentBase
    ? currentPath.split('/').filter(p => p).pop() || 'Department'
    : 'Directory'

  const stats = [
    {
      title: 'Total Users',
      value: statsData?.users || 0,
      description: `Users in ${contextLabel}`,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      href: ROUTES.USERS,
    },
    {
      title: 'Total Groups',
      value: statsData?.groups || 0,
      description: `Groups in ${contextLabel}`,
      icon: UsersRound,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      href: ROUTES.GROUPS,
    },
    {
      title: 'Roles',
      value: statsData?.roles || 0,
      description: 'Organizational roles',
      icon: Shield,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      href: ROUTES.GROUPS,
    },
    {
      title: 'Departments',
      value: statsData?.departments || 0,
      description: 'Organizational units',
      icon: Building2,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      href: ROUTES.DEPARTMENTS,
    },
  ]

  const healthServices = [
    { key: 'ldap', label: 'LDAP Server', status: healthData?.services.ldap?.status },
    { key: 'redis', label: 'Redis Cache', status: healthData?.services.redis?.status },
    { key: 'database', label: 'PostgreSQL', status: healthData?.services.database?.status },
  ]

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user?.displayName || user?.cn || 'User'}`}
        description="Here's an overview of your identity management system"
      />

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <Link key={stat.title} to={stat.href}>
            <Card className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Quick Actions
            </CardTitle>
            <CardDescription>Common administrative tasks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button asChild variant="outline" className="w-full justify-start">
              <Link to={ROUTES.USER_CREATE}>
                <UserPlus className="mr-2 h-4 w-4" />
                Create New User
              </Link>
            </Button>

            {/* Group Creation Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-full justify-between">
                  <span className="flex items-center">
                    <UsersRound className="mr-2 h-4 w-4" />
                    Create New Group
                  </span>
                  <ChevronDown className="h-4 w-4 ml-2" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuLabel>Group Type</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to={ROUTES.GROUP_CREATE} className="cursor-pointer">
                    <UsersRound className="mr-2 h-4 w-4" />
                    <div>
                      <div className="font-medium">Organizational Group</div>
                      <div className="text-xs text-muted-foreground">groupOfNames for LDAP access</div>
                    </div>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/posix/groups?create=true" className="cursor-pointer">
                    <Terminal className="mr-2 h-4 w-4" />
                    <div>
                      <div className="font-medium">POSIX Group</div>
                      <div className="text-xs text-muted-foreground">Unix/Linux system group</div>
                    </div>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/posix/mixed-groups?create=true" className="cursor-pointer">
                    <Layers className="mr-2 h-4 w-4" />
                    <div>
                      <div className="font-medium">Mixed Group</div>
                      <div className="text-xs text-muted-foreground">LDAP + POSIX hybrid</div>
                    </div>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel>Roles</DropdownMenuLabel>
                <DropdownMenuItem asChild>
                  <Link to={ROUTES.ROLE_CREATE} className="cursor-pointer">
                    <Shield className="mr-2 h-4 w-4" />
                    <div>
                      <div className="font-medium">Organizational Role</div>
                      <div className="text-xs text-muted-foreground">organizationalRole entry</div>
                    </div>
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>Latest changes in the system</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">No recent activity to display</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              System Health
            </CardTitle>
            <CardDescription>Live status of core dependencies</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {healthServices.map((service) => {
                const isOk = service.status === 'ok'
                return (
                  <div key={service.key} className="flex items-center justify-between">
                    <span className="text-sm">{service.label}</span>
                    <span
                      className={`flex items-center gap-1 text-sm ${
                        isOk ? 'text-emerald-600' : 'text-destructive'
                      }`}
                    >
                      <span
                        className={`h-2 w-2 rounded-full ${
                          isOk ? 'bg-emerald-600' : 'bg-destructive'
                        }`}
                      />
                      {isOk ? 'Online' : 'Degraded'}
                    </span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
