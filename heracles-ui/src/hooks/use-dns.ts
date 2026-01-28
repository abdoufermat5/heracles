/**
 * DNS Plugin React Query Hooks
 *
 * Custom hooks for managing DNS zones and records with TanStack Query.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dnsApi } from '@/lib/api/dns'
import type {
  DnsZoneCreate,
  DnsZoneUpdate,
  DnsRecordCreate,
  DnsRecordUpdate,
} from '@/types/dns'

// ============================================================================
// Query Keys
// ============================================================================

export const dnsQueryKeys = {
  all: ['dns'] as const,
  zones: () => [...dnsQueryKeys.all, 'zones'] as const,
  zone: (zoneName: string) => [...dnsQueryKeys.zones(), zoneName] as const,
  records: (zoneName: string) =>
    [...dnsQueryKeys.zone(zoneName), 'records'] as const,
}

// ============================================================================
// Zone Query Hooks
// ============================================================================

/**
 * Hook for listing all DNS zones
 */
export function useDnsZones() {
  return useQuery({
    queryKey: dnsQueryKeys.zones(),
    queryFn: () => dnsApi.listZones(),
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook for getting a single DNS zone
 */
export function useDnsZone(zoneName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: dnsQueryKeys.zone(zoneName),
    queryFn: () => dnsApi.getZone(zoneName),
    enabled: options?.enabled ?? !!zoneName,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Zone Mutation Hooks
// ============================================================================

/**
 * Hook for creating a DNS zone
 */
export function useCreateDnsZone() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DnsZoneCreate) => dnsApi.createZone(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zones() })
    },
  })
}

/**
 * Hook for updating a DNS zone
 */
export function useUpdateDnsZone(zoneName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DnsZoneUpdate) => dnsApi.updateZone(zoneName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zone(zoneName) })
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zones() })
    },
  })
}

/**
 * Hook for deleting a DNS zone
 */
export function useDeleteDnsZone() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (zoneName: string) => dnsApi.deleteZone(zoneName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zones() })
    },
  })
}

// ============================================================================
// Record Query Hooks
// ============================================================================

/**
 * Hook for listing records in a zone
 */
export function useDnsRecords(zoneName: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: dnsQueryKeys.records(zoneName),
    queryFn: () => dnsApi.listRecords(zoneName),
    enabled: options?.enabled ?? !!zoneName,
    staleTime: 30 * 1000,
  })
}

// ============================================================================
// Record Mutation Hooks
// ============================================================================

/**
 * Hook for creating a DNS record
 */
export function useCreateDnsRecord(zoneName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DnsRecordCreate) => dnsApi.createRecord(zoneName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.records(zoneName) })
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zone(zoneName) })
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zones() })
    },
  })
}

/**
 * Hook for updating a DNS record
 */
export function useUpdateDnsRecord(zoneName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      name,
      recordType,
      oldValue,
      data,
    }: {
      name: string
      recordType: string
      oldValue: string
      data: DnsRecordUpdate
    }) => dnsApi.updateRecord(zoneName, name, recordType, oldValue, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.records(zoneName) })
    },
  })
}

/**
 * Hook for deleting a DNS record
 */
export function useDeleteDnsRecord(zoneName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      name,
      recordType,
      value,
    }: {
      name: string
      recordType: string
      value: string
    }) => dnsApi.deleteRecord(zoneName, name, recordType, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.records(zoneName) })
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zone(zoneName) })
      queryClient.invalidateQueries({ queryKey: dnsQueryKeys.zones() })
    },
  })
}
