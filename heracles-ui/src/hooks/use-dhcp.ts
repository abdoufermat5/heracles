/**
 * DHCP Plugin React Query Hooks
 *
 * Custom hooks for managing DHCP services, subnets, pools, and hosts with TanStack Query.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dhcpApi } from '@/lib/api/dhcp'
import type {
  DhcpServiceCreate,
  DhcpServiceUpdate,
  DhcpSubnetCreate,
  DhcpSubnetUpdate,
  DhcpPoolCreate,
  DhcpPoolUpdate,
  DhcpHostCreate,
  DhcpHostUpdate,
} from '@/types/dhcp'

// ============================================================================
// Query Keys
// ============================================================================

export const dhcpQueryKeys = {
  all: ['dhcp'] as const,
  services: () => [...dhcpQueryKeys.all, 'services'] as const,
  service: (serviceCn: string) => [...dhcpQueryKeys.services(), serviceCn] as const,
  serviceTree: (serviceCn: string) => [...dhcpQueryKeys.service(serviceCn), 'tree'] as const,
  subnets: (serviceCn: string) => [...dhcpQueryKeys.service(serviceCn), 'subnets'] as const,
  subnet: (serviceCn: string, subnetCn: string) => [...dhcpQueryKeys.subnets(serviceCn), subnetCn] as const,
  pools: (serviceCn: string, parentDn: string) => [...dhcpQueryKeys.service(serviceCn), 'pools', parentDn] as const,
  hosts: (serviceCn: string) => [...dhcpQueryKeys.service(serviceCn), 'hosts'] as const,
  host: (serviceCn: string, hostCn: string) => [...dhcpQueryKeys.hosts(serviceCn), hostCn] as const,
}

// ============================================================================
// Service Query Hooks
// ============================================================================

/**
 * Hook for listing all DHCP services
 */
export function useDhcpServices(params?: { search?: string; page?: number; pageSize?: number; base?: string }) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.services(), params],
    queryFn: () => dhcpApi.listServices(params),
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook for getting a single DHCP service
 */
export function useDhcpService(serviceCn: string, options?: { enabled?: boolean; baseDn?: string }) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.service(serviceCn), { baseDn: options?.baseDn }] as const,
    queryFn: () => dhcpApi.getService(serviceCn, options?.baseDn),
    enabled: options?.enabled ?? !!serviceCn,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for getting the DHCP tree for a service
 */
export function useDhcpServiceTree(serviceCn: string, options?: { enabled?: boolean; baseDn?: string }) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.serviceTree(serviceCn), { baseDn: options?.baseDn }] as const,
    queryFn: () => dhcpApi.getServiceTree(serviceCn, options?.baseDn),
    enabled: options?.enabled ?? !!serviceCn,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Service Mutation Hooks
// ============================================================================

/**
 * Hook for creating a DHCP service
 */
export function useCreateDhcpService() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, baseDn }: { data: DhcpServiceCreate; baseDn?: string }) =>
      dhcpApi.createService(data, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.services() })
    },
  })
}

/**
 * Hook for updating a DHCP service
 */
export function useUpdateDhcpService(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, baseDn }: { data: DhcpServiceUpdate; baseDn?: string }) =>
      dhcpApi.updateService(serviceCn, data, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.service(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.services() })
    },
  })
}

/**
 * Hook for deleting a DHCP service
 */
export function useDeleteDhcpService() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ serviceCn, recursive, baseDn }: { serviceCn: string; recursive?: boolean; baseDn?: string }) =>
      dhcpApi.deleteService(serviceCn, recursive, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.services() })
    },
  })
}

// ============================================================================
// Subnet Query Hooks
// ============================================================================

/**
 * Hook for listing subnets under a service
 */
export function useDhcpSubnets(
  serviceCn: string,
  params?: { parentDn?: string; search?: string; page?: number; pageSize?: number },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.subnets(serviceCn), params],
    queryFn: () => dhcpApi.listSubnets(serviceCn, params),
    enabled: options?.enabled ?? !!serviceCn,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for getting a single subnet
 */
export function useDhcpSubnet(
  serviceCn: string,
  subnetCn: string,
  dn: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: dhcpQueryKeys.subnet(serviceCn, subnetCn),
    queryFn: () => dhcpApi.getSubnet(serviceCn, subnetCn, dn),
    enabled: options?.enabled ?? (!!serviceCn && !!subnetCn && !!dn),
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Subnet Mutation Hooks
// ============================================================================

/**
 * Hook for creating a subnet
 */
export function useCreateDhcpSubnet(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, parentDn, baseDn }: { data: DhcpSubnetCreate; parentDn?: string; baseDn?: string }) =>
      dhcpApi.createSubnet(serviceCn, data, parentDn, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.subnets(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

/**
 * Hook for updating a subnet
 */
export function useUpdateDhcpSubnet(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ subnetCn, dn, data, baseDn }: { subnetCn: string; dn: string; data: DhcpSubnetUpdate; baseDn?: string }) =>
      dhcpApi.updateSubnet(serviceCn, subnetCn, dn, data, baseDn),
    onSuccess: (_, { subnetCn }) => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.subnet(serviceCn, subnetCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.subnets(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

/**
 * Hook for deleting a subnet
 */
export function useDeleteDhcpSubnet(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ subnetCn, dn, recursive, baseDn }: { subnetCn: string; dn: string; recursive?: boolean; baseDn?: string }) =>
      dhcpApi.deleteSubnet(serviceCn, subnetCn, dn, recursive, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.subnets(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

// ============================================================================
// Pool Query Hooks
// ============================================================================

/**
 * Hook for listing pools under a parent
 */
export function useDhcpPools(
  serviceCn: string,
  parentDn: string,
  params?: { search?: string; page?: number; pageSize?: number },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.pools(serviceCn, parentDn), params],
    queryFn: () => dhcpApi.listPools(serviceCn, parentDn, params),
    enabled: options?.enabled ?? (!!serviceCn && !!parentDn),
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Pool Mutation Hooks
// ============================================================================

/**
 * Hook for creating a pool
 */
export function useCreateDhcpPool(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ parentDn, data, baseDn }: { parentDn: string; data: DhcpPoolCreate; baseDn?: string }) =>
      dhcpApi.createPool(serviceCn, parentDn, data, baseDn),
    onSuccess: (_, { parentDn }) => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.pools(serviceCn, parentDn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

/**
 * Hook for updating a pool
 */
export function useUpdateDhcpPool(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ poolCn, dn, data, baseDn }: { poolCn: string; dn: string; data: DhcpPoolUpdate; baseDn?: string }) =>
      dhcpApi.updatePool(serviceCn, poolCn, dn, data, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.all })
    },
  })
}

/**
 * Hook for deleting a pool
 */
export function useDeleteDhcpPool(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ poolCn, dn, baseDn }: { poolCn: string; dn: string; baseDn?: string }) =>
      dhcpApi.deletePool(serviceCn, poolCn, dn, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.all })
    },
  })
}

// ============================================================================
// Host Query Hooks
// ============================================================================

/**
 * Hook for listing hosts under a service
 */
export function useDhcpHosts(
  serviceCn: string,
  params?: { parentDn?: string; search?: string; page?: number; pageSize?: number },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...dhcpQueryKeys.hosts(serviceCn), params],
    queryFn: () => dhcpApi.listHosts(serviceCn, params),
    enabled: options?.enabled ?? !!serviceCn,
    staleTime: 30 * 1000,
  })
}

/**
 * Hook for getting a single host
 */
export function useDhcpHost(
  serviceCn: string,
  hostCn: string,
  dn: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: dhcpQueryKeys.host(serviceCn, hostCn),
    queryFn: () => dhcpApi.getHost(serviceCn, hostCn, dn),
    enabled: options?.enabled ?? (!!serviceCn && !!hostCn && !!dn),
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Host Mutation Hooks
// ============================================================================

/**
 * Hook for creating a host
 */
export function useCreateDhcpHost(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ data, parentDn, baseDn }: { data: DhcpHostCreate; parentDn?: string; baseDn?: string }) =>
      dhcpApi.createHost(serviceCn, data, parentDn, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.hosts(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

/**
 * Hook for updating a host
 */
export function useUpdateDhcpHost(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ hostCn, dn, data, baseDn }: { hostCn: string; dn: string; data: DhcpHostUpdate; baseDn?: string }) =>
      dhcpApi.updateHost(serviceCn, hostCn, dn, data, baseDn),
    onSuccess: (_, { hostCn }) => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.host(serviceCn, hostCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.hosts(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}

/**
 * Hook for deleting a host
 */
export function useDeleteDhcpHost(serviceCn: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ hostCn, dn, baseDn }: { hostCn: string; dn: string; baseDn?: string }) =>
      dhcpApi.deleteHost(serviceCn, hostCn, dn, baseDn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.hosts(serviceCn) })
      queryClient.invalidateQueries({ queryKey: dhcpQueryKeys.serviceTree(serviceCn) })
    },
  })
}
