import { Link } from 'react-router-dom'
import { Users, UsersRound, Server, Activity, TrendingUp, UserPlus, ChevronDown, Terminal, Layers, Shield } from 'lucide-react'
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
import { PageHeader, LoadingPage, ErrorDisplay } from '@/components/common'
import { useUsers, useGroups } from '@/hooks'
import { useAuthStore, useDepartmentStore } from '@/stores'
import { ROUTES, PLUGIN_ROUTES } from '@/config/constants'

export function DashboardPage() {
  const { user } = useAuthStore()
  const { currentBase, currentPath } = useDepartmentStore()

  // Pass department context to hooks for contextual data
  const { data: usersData, isLoading: usersLoading, error: usersError } = useUsers({
    page_size: 1,
    base: currentBase || undefined
  })
  const { data: groupsData, isLoading: groupsLoading, error: groupsError } = useGroups({
    page_size: 1,
    base: currentBase || undefined
  })

  if (usersLoading || groupsLoading) {
    return <LoadingPage message="Loading dashboard..." />
  }

  if (usersError || groupsError) {
    return (
      <ErrorDisplay
        message={(usersError || groupsError)?.message || 'Failed to load dashboard data'}
      />
    )
  }

  // Determine context label
  const contextLabel = currentBase
    ? currentPath.split('/').filter(p => p).pop() || 'Department'
    : 'All'

  const stats = [
    {
      title: 'Total Users',
      value: usersData?.total || 0,
      description: `Users in ${contextLabel}`,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      href: ROUTES.USERS,
    },
    {
      title: 'Total Groups',
      value: groupsData?.total || 0,
      description: `Groups in ${contextLabel}`,
      icon: UsersRound,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      href: ROUTES.GROUPS,
    },
    {
      title: 'Systems',
      value: 0,
      description: 'Managed systems',
      icon: Server,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      href: PLUGIN_ROUTES.SYSTEMS.LIST,
    },
    {
      title: 'Activity',
      value: '-',
      description: 'Recent changes',
      icon: Activity,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      href: '#',
    },
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
              System Status
            </CardTitle>
            <CardDescription>Services health overview</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">LDAP Server</span>
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <span className="h-2 w-2 rounded-full bg-green-600" />
                  Online
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">API Server</span>
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <span className="h-2 w-2 rounded-full bg-green-600" />
                  Online
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
