/**
 * DHCP Plugin API Client
 *
 * API client functions for DHCP service, subnet, pool, and host management.
 */

import { apiClient } from '../api-client'
import type {
  DhcpService,
  DhcpServiceCreate,
  DhcpServiceUpdate,
  DhcpServiceListResponse,
  DhcpSubnet,
  DhcpSubnetCreate,
  DhcpSubnetUpdate,
  DhcpSubnetListResponse,
  DhcpPool,
  DhcpPoolCreate,
  DhcpPoolUpdate,
  DhcpPoolListResponse,
  DhcpHost,
  DhcpHostCreate,
  DhcpHostUpdate,
  DhcpHostListResponse,
  DhcpTree,
} from '@/types/dhcp'

const BASE_PATH = '/dhcp'

// ============================================================================
// Service API Functions
// ============================================================================

/**
 * List all DHCP services
 */
export async function listServices(
  params?: { search?: string; page?: number; pageSize?: number }
): Promise<DhcpServiceListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.search) searchParams.set('search', params.search)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString())
  
  const query = searchParams.toString()
  return apiClient.get<DhcpServiceListResponse>(`${BASE_PATH}${query ? `?${query}` : ''}`)
}

/**
 * Get a single DHCP service by name
 */
export async function getService(serviceCn: string): Promise<DhcpService> {
  return apiClient.get<DhcpService>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}`
  )
}

/**
 * Create a new DHCP service
 */
export async function createService(data: DhcpServiceCreate): Promise<DhcpService> {
  return apiClient.post<DhcpService>(`${BASE_PATH}`, data)
}

/**
 * Update a DHCP service
 */
export async function updateService(
  serviceCn: string,
  data: DhcpServiceUpdate
): Promise<DhcpService> {
  return apiClient.patch<DhcpService>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}`,
    data
  )
}

/**
 * Delete a DHCP service
 */
export async function deleteService(serviceCn: string, recursive?: boolean): Promise<void> {
  const query = recursive ? '?recursive=true' : ''
  return apiClient.delete(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}${query}`
  )
}

/**
 * Get the DHCP tree for a service
 */
export async function getServiceTree(serviceCn: string): Promise<DhcpTree> {
  return apiClient.get<DhcpTree>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/tree`
  )
}

// ============================================================================
// Subnet API Functions
// ============================================================================

/**
 * List subnets under a service
 */
export async function listSubnets(
  serviceCn: string,
  params?: { parentDn?: string; search?: string; page?: number; pageSize?: number }
): Promise<DhcpSubnetListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.parentDn) searchParams.set('parent_dn', params.parentDn)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString())
  
  const query = searchParams.toString()
  return apiClient.get<DhcpSubnetListResponse>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/subnets${query ? `?${query}` : ''}`
  )
}

/**
 * Get a single subnet by DN
 */
export async function getSubnet(serviceCn: string, subnetCn: string, dn: string): Promise<DhcpSubnet> {
  return apiClient.get<DhcpSubnet>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/subnets/${encodeURIComponent(subnetCn)}?dn=${encodeURIComponent(dn)}`
  )
}

/**
 * Create a new subnet
 */
export async function createSubnet(
  serviceCn: string,
  data: DhcpSubnetCreate,
  parentDn?: string
): Promise<DhcpSubnet> {
  const query = parentDn ? `?parent_dn=${encodeURIComponent(parentDn)}` : ''
  return apiClient.post<DhcpSubnet>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/subnets${query}`,
    data
  )
}

/**
 * Update a subnet
 */
export async function updateSubnet(
  serviceCn: string,
  subnetCn: string,
  dn: string,
  data: DhcpSubnetUpdate
): Promise<DhcpSubnet> {
  return apiClient.patch<DhcpSubnet>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/subnets/${encodeURIComponent(subnetCn)}?dn=${encodeURIComponent(dn)}`,
    data
  )
}

/**
 * Delete a subnet
 */
export async function deleteSubnet(
  serviceCn: string,
  subnetCn: string,
  dn: string,
  recursive?: boolean
): Promise<void> {
  const params = new URLSearchParams({ dn })
  if (recursive) params.set('recursive', 'true')
  return apiClient.delete(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/subnets/${encodeURIComponent(subnetCn)}?${params}`
  )
}

// ============================================================================
// Pool API Functions
// ============================================================================

/**
 * List pools under a parent (subnet or shared network)
 */
export async function listPools(
  serviceCn: string,
  parentDn: string,
  params?: { search?: string; page?: number; pageSize?: number }
): Promise<DhcpPoolListResponse> {
  const searchParams = new URLSearchParams({ parent_dn: parentDn })
  if (params?.search) searchParams.set('search', params.search)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString())
  
  return apiClient.get<DhcpPoolListResponse>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/pools?${searchParams}`
  )
}

/**
 * Create a new pool
 */
export async function createPool(
  serviceCn: string,
  parentDn: string,
  data: DhcpPoolCreate
): Promise<DhcpPool> {
  return apiClient.post<DhcpPool>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/pools?parent_dn=${encodeURIComponent(parentDn)}`,
    data
  )
}

/**
 * Update a pool
 */
export async function updatePool(
  serviceCn: string,
  poolCn: string,
  dn: string,
  data: DhcpPoolUpdate
): Promise<DhcpPool> {
  return apiClient.patch<DhcpPool>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/pools/${encodeURIComponent(poolCn)}?dn=${encodeURIComponent(dn)}`,
    data
  )
}

/**
 * Delete a pool
 */
export async function deletePool(
  serviceCn: string,
  poolCn: string,
  dn: string
): Promise<void> {
  return apiClient.delete(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/pools/${encodeURIComponent(poolCn)}?dn=${encodeURIComponent(dn)}`
  )
}

// ============================================================================
// Host API Functions
// ============================================================================

/**
 * List hosts under a service (searches all levels)
 */
export async function listHosts(
  serviceCn: string,
  params?: { parentDn?: string; search?: string; page?: number; pageSize?: number }
): Promise<DhcpHostListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.parentDn) searchParams.set('parent_dn', params.parentDn)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString())
  
  const query = searchParams.toString()
  return apiClient.get<DhcpHostListResponse>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/hosts${query ? `?${query}` : ''}`
  )
}

/**
 * Get a single host by DN
 */
export async function getHost(serviceCn: string, hostCn: string, dn: string): Promise<DhcpHost> {
  return apiClient.get<DhcpHost>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/hosts/${encodeURIComponent(hostCn)}?dn=${encodeURIComponent(dn)}`
  )
}

/**
 * Create a new host
 */
export async function createHost(
  serviceCn: string,
  data: DhcpHostCreate,
  parentDn?: string
): Promise<DhcpHost> {
  const query = parentDn ? `?parent_dn=${encodeURIComponent(parentDn)}` : ''
  return apiClient.post<DhcpHost>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/hosts${query}`,
    data
  )
}

/**
 * Update a host
 */
export async function updateHost(
  serviceCn: string,
  hostCn: string,
  dn: string,
  data: DhcpHostUpdate
): Promise<DhcpHost> {
  return apiClient.patch<DhcpHost>(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/hosts/${encodeURIComponent(hostCn)}?dn=${encodeURIComponent(dn)}`,
    data
  )
}

/**
 * Delete a host
 */
export async function deleteHost(
  serviceCn: string,
  hostCn: string,
  dn: string
): Promise<void> {
  return apiClient.delete(
    `${BASE_PATH}/${encodeURIComponent(serviceCn)}/hosts/${encodeURIComponent(hostCn)}?dn=${encodeURIComponent(dn)}`
  )
}

// Export all functions as a namespace
export const dhcpApi = {
  // Services
  listServices,
  getService,
  createService,
  updateService,
  deleteService,
  getServiceTree,
  // Subnets
  listSubnets,
  getSubnet,
  createSubnet,
  updateSubnet,
  deleteSubnet,
  // Pools
  listPools,
  createPool,
  updatePool,
  deletePool,
  // Hosts
  listHosts,
  getHost,
  createHost,
  updateHost,
  deleteHost,
}
