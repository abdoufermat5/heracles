import { apiClient } from '../api-client'
import type {
  AclPermission,
  AclAttributeGroup,
  AclPolicy,
  AclPolicyListResponse,
  AclPolicyAttrRule,
  AclAssignment,
  AclAssignmentListResponse,
  AuditLogListResponse,
  MyPermissionsResponse,
  CreatePolicyData,
  UpdatePolicyData,
  CreateAssignmentData,
  UpdateAssignmentData,
  CreatePolicyAttrRuleData,
  AclPolicyListParams,
  AclAssignmentListParams,
  AuditLogListParams,
} from '@/types/acl'

type ApiParams = Record<string, string | number | undefined>

export const aclApi = {
  // Permissions (read-only)
  listPermissions: async (): Promise<AclPermission[]> => {
    return apiClient.get<AclPermission[]>('/acl/permissions')
  },

  // Attribute Groups (read-only)
  listAttributeGroups: async (objectType?: string): Promise<AclAttributeGroup[]> => {
    const params = objectType ? { object_type: objectType } : undefined
    return apiClient.get<AclAttributeGroup[]>('/acl/attribute-groups', params)
  },

  // Policies
  listPolicies: async (params?: AclPolicyListParams): Promise<AclPolicyListResponse> => {
    return apiClient.get<AclPolicyListResponse>('/acl/policies', params as ApiParams)
  },

  getPolicy: async (id: string): Promise<AclPolicy> => {
    return apiClient.get<AclPolicy>(`/acl/policies/${id}`)
  },

  createPolicy: async (data: CreatePolicyData): Promise<AclPolicy> => {
    return apiClient.post<AclPolicy>('/acl/policies', data)
  },

  updatePolicy: async (id: string, data: UpdatePolicyData): Promise<AclPolicy> => {
    return apiClient.patch<AclPolicy>(`/acl/policies/${id}`, data)
  },

  deletePolicy: async (id: string): Promise<void> => {
    await apiClient.delete(`/acl/policies/${id}`)
  },

  // Policy Attribute Rules
  listPolicyAttrRules: async (policyId: string): Promise<AclPolicyAttrRule[]> => {
    return apiClient.get<AclPolicyAttrRule[]>(`/acl/policies/${policyId}/attr-rules`)
  },

  createPolicyAttrRule: async (policyId: string, data: CreatePolicyAttrRuleData): Promise<AclPolicyAttrRule> => {
    return apiClient.post<AclPolicyAttrRule>(`/acl/policies/${policyId}/attr-rules`, data)
  },

  deletePolicyAttrRule: async (policyId: string, ruleId: string): Promise<void> => {
    await apiClient.delete(`/acl/policies/${policyId}/attr-rules/${ruleId}`)
  },

  // Assignments
  listAssignments: async (params?: AclAssignmentListParams): Promise<AclAssignmentListResponse> => {
    return apiClient.get<AclAssignmentListResponse>('/acl/assignments', params as ApiParams)
  },

  getAssignment: async (id: string): Promise<AclAssignment> => {
    return apiClient.get<AclAssignment>(`/acl/assignments/${id}`)
  },

  createAssignment: async (data: CreateAssignmentData): Promise<AclAssignment> => {
    return apiClient.post<AclAssignment>('/acl/assignments', data)
  },

  updateAssignment: async (id: string, data: UpdateAssignmentData): Promise<AclAssignment> => {
    return apiClient.patch<AclAssignment>(`/acl/assignments/${id}`, data)
  },

  deleteAssignment: async (id: string): Promise<void> => {
    await apiClient.delete(`/acl/assignments/${id}`)
  },

  // My Permissions
  getMyPermissions: async (): Promise<MyPermissionsResponse> => {
    return apiClient.get<MyPermissionsResponse>('/acl/me/permissions')
  },

  // Audit Log
  listAuditLogs: async (params?: AuditLogListParams): Promise<AuditLogListResponse> => {
    const { result, ...rest } = params ?? {}
    const queryParams: ApiParams = {
      ...rest,
      ...(result !== undefined && { result: String(result) }),
    }
    return apiClient.get<AuditLogListResponse>('/acl/audit', queryParams)
  },
}
