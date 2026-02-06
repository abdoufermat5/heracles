import { UserCircle, ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, LoadingPage, ErrorDisplay } from '@/components/common'
import { PermissionBadges } from '@/components/acl'
import { useMyPermissions } from '@/hooks'
import { useAuthStore } from '@/stores'

export function ProfilePage() {
  const user = useAuthStore((state) => state.user)
  const { data: permsData, isLoading, error, refetch } = useMyPermissions()

  if (isLoading) {
    return <LoadingPage message="Loading profile..." />
  }

  if (error) {
    return <ErrorDisplay message={error.message} onRetry={() => refetch()} />
  }

  return (
    <div>
      <PageHeader
        title="My Profile"
        description="View your account details and effective permissions"
      />

      <div className="space-y-6">
        {/* User Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircle className="h-5 w-5" />
              Account Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Username</p>
                <p className="text-sm font-mono">{user?.uid}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Display Name</p>
                <p className="text-sm">{user?.displayName || user?.cn || '—'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Email</p>
                <p className="text-sm">{user?.mail || '—'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">DN</p>
                <p className="text-sm font-mono break-all">{permsData?.userDn || user?.dn || '—'}</p>
              </div>
              {user?.groups && user.groups.length > 0 && (
                <div className="sm:col-span-2">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Groups</p>
                  <div className="flex flex-wrap gap-1">
                    {user.groups.map((g) => (
                      <Badge key={g} variant="outline" className="text-xs">
                        {g}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Effective Permissions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Effective Permissions
              <Badge variant="secondary">
                {permsData?.permissions.length || 0}
              </Badge>
            </CardTitle>
            <CardDescription>
              These are all the permissions you currently have, resolved from your policy assignments.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PermissionBadges permissions={permsData?.permissions ?? []} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
