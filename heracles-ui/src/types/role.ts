// Role Types

export interface Role {
    dn: string
    cn: string
    description?: string
    members: string[]
    memberCount: number
}

export interface RoleListResponse {
    roles: Role[]
    total: number
    page: number
    pageSize: number
    hasMore: boolean
}

export interface RoleCreateData {
    cn: string
    description?: string
    departmentDn?: string
    members?: string[]
}

export interface RoleUpdateData {
    description?: string
}
