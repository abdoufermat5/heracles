// ACL Types

export interface AclPermission {
  bitPosition: number
  name: string
  scope: string
  action: string
  description: string
  plugin: string | null
}

export interface AclAttributeGroup {
  id: number
  objectType: string
  groupName: string
  label: string
  attributes: string[]
  plugin: string | null
}

export interface AclPolicy {
  id: string
  name: string
  description: string | null
  permissions: string[]
  builtin: boolean
  createdAt: string
  updatedAt: string
}

export interface AclPolicyListResponse {
  policies: AclPolicy[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export interface AclPolicyAttrRule {
  id: string
  policyId: string
  objectType: string
  action: string
  ruleType: string
  attrGroups: string[]
}

export interface AclPolicyDetail extends AclPolicy {
  attrRules: AclPolicyAttrRule[]
}

export interface AclAssignment {
  id: string
  policyId: string
  policyName: string
  subjectType: 'user' | 'group' | 'role'
  subjectDn: string
  scopeDn: string
  scopeType: 'base' | 'subtree'
  selfOnly: boolean
  deny: boolean
  priority: number
  builtin: boolean
  createdAt: string
}

export interface AclAssignmentListResponse {
  assignments: AclAssignment[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export interface AuditLogEntry {
  id: number
  ts: string
  userDn: string
  action: string
  targetDn: string | null
  permission: string | null
  result: boolean | null
  details: Record<string, unknown> | null
}

export interface AuditLogListResponse {
  entries: AuditLogEntry[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export interface MyPermissionsResponse {
  userDn: string
  permissions: string[]
}

// Form data types
export interface CreatePolicyData {
  name: string
  description?: string
  permissions: string[]
}

export interface UpdatePolicyData {
  name?: string
  description?: string
  permissions?: string[]
}

export interface CreateAssignmentData {
  policyId: string
  subjectType: 'user' | 'group' | 'role'
  subjectDn: string
  scopeDn?: string
  scopeType?: 'base' | 'subtree'
  selfOnly?: boolean
  deny?: boolean
  priority?: number
}

export interface UpdateAssignmentData {
  scopeDn?: string
  scopeType?: 'base' | 'subtree'
  selfOnly?: boolean
  deny?: boolean
  priority?: number
}

export interface CreatePolicyAttrRuleData {
  objectType: string
  action: 'read' | 'write'
  ruleType: 'allow' | 'deny'
  attrGroups: string[]
}

// Query param types
export interface AclPolicyListParams {
  page?: number
  page_size?: number
  builtin?: boolean
}

export interface AclAssignmentListParams {
  page?: number
  page_size?: number
  policy_id?: string
  subject_dn?: string
}

export interface AuditLogListParams {
  page?: number
  page_size?: number
  user_dn?: string
  action?: string
  target_dn?: string
  result?: boolean
  fromTs?: string
  toTs?: string
}
