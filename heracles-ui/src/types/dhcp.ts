/**
 * DHCP Plugin Types
 *
 * TypeScript type definitions for DHCP management
 */

// ============================================================================
// DHCP Object Types
// ============================================================================

export const DHCP_OBJECT_TYPES = [
  'service',
  'shared_network',
  'subnet',
  'pool',
  'host',
  'group',
  'class',
  'subclass',
  'tsig_key',
  'dns_zone',
  'failover_peer',
] as const

export type DhcpObjectType = (typeof DHCP_OBJECT_TYPES)[number]

export const DHCP_OBJECT_TYPE_LABELS: Record<DhcpObjectType, string> = {
  service: 'DHCP Service',
  shared_network: 'Shared Network',
  subnet: 'Subnet',
  pool: 'Pool',
  host: 'Host',
  group: 'Group',
  class: 'Class',
  subclass: 'SubClass',
  tsig_key: 'TSIG Key',
  dns_zone: 'DNS Zone',
  failover_peer: 'Failover Peer',
}

export const DHCP_OBJECT_TYPE_ICONS: Record<DhcpObjectType, string> = {
  service: 'Server',
  shared_network: 'Network',
  subnet: 'Blocks',
  pool: 'Layers',
  host: 'Monitor',
  group: 'Users',
  class: 'Tag',
  subclass: 'Tags',
  tsig_key: 'Key',
  dns_zone: 'Globe',
  failover_peer: 'RefreshCw',
}

// ============================================================================
// TSIG Key Algorithms
// ============================================================================

export const TSIG_KEY_ALGORITHMS = [
  'hmac-md5',
  'hmac-sha1',
  'hmac-sha256',
  'hmac-sha512',
] as const

export type TsigKeyAlgorithm = (typeof TSIG_KEY_ALGORITHMS)[number]

export const TSIG_KEY_ALGORITHM_LABELS: Record<TsigKeyAlgorithm, string> = {
  'hmac-md5': 'HMAC-MD5',
  'hmac-sha1': 'HMAC-SHA1',
  'hmac-sha256': 'HMAC-SHA256',
  'hmac-sha512': 'HMAC-SHA512',
}

// ============================================================================
// DHCP Service Types
// ============================================================================

export interface DhcpService {
  dn: string
  cn: string
  dhcpPrimaryDN?: string | null
  dhcpSecondaryDN?: string | null
  dhcpStatements: string[]
  dhcpOption: string[]
  dhcpComments?: string | null
  objectType: 'service'
}

export interface DhcpServiceCreate {
  cn: string
  comments?: string
  dhcpStatements?: string[]
  dhcpOptions?: string[]
  dhcpPrimaryDn?: string
  dhcpSecondaryDn?: string
}

export interface DhcpServiceUpdate {
  comments?: string
  dhcpStatements?: string[]
  dhcpOptions?: string[]
  dhcpPrimaryDn?: string
  dhcpSecondaryDn?: string
}

export interface DhcpServiceListItem {
  dn: string
  cn: string
  dhcpComments?: string | null
  subnetCount?: number
  hostCount?: number
  objectType: 'service'
}

// ============================================================================
// DHCP Subnet Types
// ============================================================================

export interface DhcpSubnet {
  dn: string
  cn: string
  dhcpNetMask: number
  dhcpRange?: string[]
  dhcpStatements: string[]
  dhcpOption: string[]
  dhcpComments?: string | null
  parentDn: string
  objectType: 'subnet'
}

export interface DhcpSubnetCreate {
  cn: string
  dhcpNetMask: number
  comments?: string
  dhcpRange?: string[]
  dhcpStatements?: string[]
  dhcpOptions?: string[]
}

export interface DhcpSubnetUpdate {
  dhcpNetMask?: number
  comments?: string
  dhcpRange?: string[]
  dhcpStatements?: string[]
  dhcpOptions?: string[]
}

export interface DhcpSubnetListItem {
  dn: string
  cn: string
  dhcpNetMask: number
  dhcpRange?: string[]
  dhcpComments?: string | null
  objectType: 'subnet'
}

// ============================================================================
// DHCP Pool Types
// ============================================================================

export interface DhcpPool {
  dn: string
  cn: string
  dhcpRange: string[]
  dhcpComments?: string | null
  dhcpPermitList?: string[]
  dhcpStatements: string[]
  dhcpOption: string[]
  failoverPeerDn?: string | null
  parentDn: string
  objectType: 'pool'
}

export interface DhcpPoolCreate {
  cn: string
  dhcpRange: string[]
  comments?: string
  dhcpPermitList?: string[]
  dhcpStatements?: string[]
  dhcpOptions?: string[]
  failoverPeerDn?: string
}

export interface DhcpPoolUpdate {
  dhcpRange?: string[]
  comments?: string
  dhcpPermitList?: string[]
  dhcpStatements?: string[]
  dhcpOptions?: string[]
  failoverPeerDn?: string
}

export interface DhcpPoolListItem {
  dn: string
  cn: string
  dhcpRange: string[]
  dhcpComments?: string | null
  objectType: 'pool'
}

// ============================================================================
// DHCP Host Types
// ============================================================================

export interface DhcpHost {
  dn: string
  cn: string
  dhcpHWAddress?: string | null
  fixedAddress?: string | null
  dhcpStatements: string[]
  dhcpOption: string[]
  dhcpComments?: string | null
  parentDn: string
  systemDn?: string | null
  objectType: 'host'
}

export interface DhcpHostCreate {
  cn: string
  dhcpHWAddress?: string
  fixedAddress?: string
  comments?: string
  dhcpStatements?: string[]
  dhcpOptions?: string[]
}

export interface DhcpHostUpdate {
  dhcpHWAddress?: string
  fixedAddress?: string
  comments?: string
  dhcpStatements?: string[]
  dhcpOptions?: string[]
}

export interface DhcpHostListItem {
  dn: string
  cn: string
  dhcpHWAddress?: string | null
  fixedAddress?: string | null
  dhcpComments?: string | null
  objectType: 'host'
}

// ============================================================================
// DHCP Shared Network Types
// ============================================================================

export interface DhcpSharedNetworkData {
  dn: string
  cn: string
  description?: string
  statements: string[]
  options: string[]
}

export interface DhcpSharedNetworkCreate {
  cn: string
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpSharedNetworkUpdate {
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpSharedNetworkListItem {
  dn: string
  cn: string
  description?: string
  subnet_count?: number
}

// ============================================================================
// DHCP Group Types
// ============================================================================

export interface DhcpGroupData {
  dn: string
  cn: string
  description?: string
  statements: string[]
  options: string[]
  host_dns: string[]
}

export interface DhcpGroupCreate {
  cn: string
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpGroupUpdate {
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpGroupListItem {
  dn: string
  cn: string
  description?: string
  host_count?: number
}

// ============================================================================
// DHCP Class Types
// ============================================================================

export interface DhcpClassData {
  dn: string
  cn: string
  description?: string
  statements: string[]
  options: string[]
  subclass_dns: string[]
}

export interface DhcpClassCreate {
  cn: string
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpClassUpdate {
  description?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpClassListItem {
  dn: string
  cn: string
  description?: string
  subclass_count?: number
}

// ============================================================================
// DHCP SubClass Types
// ============================================================================

export interface DhcpSubClassData {
  dn: string
  cn: string
  description?: string
  class_data?: string
  statements: string[]
  options: string[]
}

export interface DhcpSubClassCreate {
  cn: string
  description?: string
  class_data?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpSubClassUpdate {
  description?: string
  class_data?: string
  statements?: string[]
  options?: string[]
}

export interface DhcpSubClassListItem {
  dn: string
  cn: string
  description?: string
  class_data?: string
}

// ============================================================================
// DHCP TSIG Key Types
// ============================================================================

export interface DhcpTsigKeyData {
  dn: string
  cn: string
  description?: string
  algorithm: TsigKeyAlgorithm
  secret: string
}

export interface DhcpTsigKeyCreate {
  cn: string
  algorithm: TsigKeyAlgorithm
  secret: string
  description?: string
}

export interface DhcpTsigKeyUpdate {
  description?: string
  algorithm?: TsigKeyAlgorithm
  secret?: string
}

export interface DhcpTsigKeyListItem {
  dn: string
  cn: string
  description?: string
  algorithm: TsigKeyAlgorithm
}

// ============================================================================
// DHCP DNS Zone Types
// ============================================================================

export interface DhcpDnsZoneData {
  dn: string
  cn: string
  description?: string
  dns_server: string
  tsig_key_dn?: string
}

export interface DhcpDnsZoneCreate {
  cn: string
  dns_server: string
  description?: string
  tsig_key_dn?: string
}

export interface DhcpDnsZoneUpdate {
  description?: string
  dns_server?: string
  tsig_key_dn?: string
}

export interface DhcpDnsZoneListItem {
  dn: string
  cn: string
  description?: string
  dns_server: string
}

// ============================================================================
// DHCP Failover Peer Types
// ============================================================================

export interface DhcpFailoverPeerData {
  dn: string
  cn: string
  description?: string
  primary_server: string
  secondary_server: string
  primary_port: number
  secondary_port: number
  response_delay?: number
  unacked_updates?: number
  max_client_lead_time?: number
  split?: number
  load_balance_time?: number
}

export interface DhcpFailoverPeerCreate {
  cn: string
  primary_server: string
  secondary_server: string
  primary_port: number
  secondary_port: number
  description?: string
  response_delay?: number
  unacked_updates?: number
  max_client_lead_time?: number
  split?: number
  load_balance_time?: number
}

export interface DhcpFailoverPeerUpdate {
  description?: string
  primary_server?: string
  secondary_server?: string
  primary_port?: number
  secondary_port?: number
  response_delay?: number
  unacked_updates?: number
  max_client_lead_time?: number
  split?: number
  load_balance_time?: number
}

export interface DhcpFailoverPeerListItem {
  dn: string
  cn: string
  description?: string
  primary_server: string
  secondary_server: string
}

// ============================================================================
// Tree Types
// ============================================================================

export interface DhcpTreeNode {
  dn: string
  cn: string
  objectType: DhcpObjectType
  dhcpComments?: string | null
  children: DhcpTreeNode[]
}

export interface DhcpTree {
  service: DhcpTreeNode
}

// ============================================================================
// List Response Types
// ============================================================================

export interface DhcpListResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type DhcpServiceListResponse = DhcpListResponse<DhcpServiceListItem>
export type DhcpSubnetListResponse = DhcpListResponse<DhcpSubnetListItem>
export type DhcpPoolListResponse = DhcpListResponse<DhcpPoolListItem>
export type DhcpHostListResponse = DhcpListResponse<DhcpHostListItem>
export type DhcpSharedNetworkListResponse = DhcpListResponse<DhcpSharedNetworkListItem>
export type DhcpGroupListResponse = DhcpListResponse<DhcpGroupListItem>
export type DhcpClassListResponse = DhcpListResponse<DhcpClassListItem>
export type DhcpSubClassListResponse = DhcpListResponse<DhcpSubClassListItem>
export type DhcpTsigKeyListResponse = DhcpListResponse<DhcpTsigKeyListItem>
export type DhcpDnsZoneListResponse = DhcpListResponse<DhcpDnsZoneListItem>
export type DhcpFailoverPeerListResponse = DhcpListResponse<DhcpFailoverPeerListItem>
