import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rolesApi } from '@/lib/api'
import type { RoleCreateData, RoleUpdateData, PaginationParams } from '@/types'

export const roleKeys = {
    all: ['roles'] as const,
    lists: () => [...roleKeys.all, 'list'] as const,
    list: (params?: PaginationParams) => [...roleKeys.lists(), params] as const,
    details: () => [...roleKeys.all, 'detail'] as const,
    detail: (cn: string) => [...roleKeys.details(), cn] as const,
}

export function useRoles(params?: PaginationParams) {
    return useQuery({
        queryKey: roleKeys.list(params),
        queryFn: () => rolesApi.list(params),
    })
}

export function useRole(cn: string) {
    return useQuery({
        queryKey: roleKeys.detail(cn),
        queryFn: () => rolesApi.get(cn),
        enabled: !!cn,
    })
}

export function useCreateRole() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: RoleCreateData) => rolesApi.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: roleKeys.lists() })
        },
    })
}

export function useUpdateRole(cn: string) {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: RoleUpdateData) => rolesApi.update(cn, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: roleKeys.detail(cn) })
            queryClient.invalidateQueries({ queryKey: roleKeys.lists() })
        },
    })
}

export function useDeleteRole() {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (cn: string) => rolesApi.delete(cn),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: roleKeys.lists() })
        },
    })
}

export function useAddRoleMember(cn: string) {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (uid: string) => rolesApi.addMember(cn, uid),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: roleKeys.detail(cn) })
        },
    })
}

export function useRemoveRoleMember(cn: string) {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (uid: string) => rolesApi.removeMember(cn, uid),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: roleKeys.detail(cn) })
        },
    })
}
