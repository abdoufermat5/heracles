import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aclApi } from '@/lib/api/acl'
import type {
  CreatePolicyData,
  UpdatePolicyData,
  CreateAssignmentData,
  UpdateAssignmentData,
  CreatePolicyAttrRuleData,
  AclPolicyListParams,
  AclAssignmentListParams,
  AuditLogListParams,
} from '@/types/acl'
import { useMutationErrorHandler, commonErrorMessages } from './use-mutation-error-handler'

// ============================================================================
// Query Key Factory
// ============================================================================

export const aclKeys = {
  all: ['acl'] as const,
  permissions: () => [...aclKeys.all, 'permissions'] as const,
  attributeGroups: (objectType?: string) => [...aclKeys.all, 'attribute-groups', objectType] as const,
  policies: () => [...aclKeys.all, 'policies'] as const,
  policyList: (params?: AclPolicyListParams) => [...aclKeys.policies(), 'list', params] as const,
  policyDetails: () => [...aclKeys.policies(), 'detail'] as const,
  policyDetail: (id: string) => [...aclKeys.policyDetails(), id] as const,
  policyAttrRules: (policyId: string) => [...aclKeys.policyDetail(policyId), 'attr-rules'] as const,
  assignments: () => [...aclKeys.all, 'assignments'] as const,
  assignmentList: (params?: AclAssignmentListParams) => [...aclKeys.assignments(), 'list', params] as const,
  assignmentDetails: () => [...aclKeys.assignments(), 'detail'] as const,
  assignmentDetail: (id: string) => [...aclKeys.assignmentDetails(), id] as const,
  myPermissions: () => [...aclKeys.all, 'my-permissions'] as const,
  auditLogs: () => [...aclKeys.all, 'audit'] as const,
  auditLogList: (params?: AuditLogListParams) => [...aclKeys.auditLogs(), 'list', params] as const,
}

// ============================================================================
// Permission & Attribute Group Queries
// ============================================================================

export function useAclPermissions() {
  return useQuery({
    queryKey: aclKeys.permissions(),
    queryFn: () => aclApi.listPermissions(),
    staleTime: 5 * 60 * 1000, // 5 minutes — permissions rarely change
  })
}

export function useAclAttributeGroups(objectType?: string) {
  return useQuery({
    queryKey: aclKeys.attributeGroups(objectType),
    queryFn: () => aclApi.listAttributeGroups(objectType),
    staleTime: 5 * 60 * 1000,
  })
}

// ============================================================================
// Policy Queries & Mutations
// ============================================================================

export function useAclPolicies(params?: AclPolicyListParams) {
  return useQuery({
    queryKey: aclKeys.policyList(params),
    queryFn: () => aclApi.listPolicies(params),
  })
}

export function useAclPolicy(id: string) {
  return useQuery({
    queryKey: aclKeys.policyDetail(id),
    queryFn: () => aclApi.getPolicy(id),
    enabled: !!id,
  })
}

export function useAclPolicyAttrRules(policyId: string) {
  return useQuery({
    queryKey: aclKeys.policyAttrRules(policyId),
    queryFn: () => aclApi.listPolicyAttrRules(policyId),
    enabled: !!policyId,
  })
}

export function useCreatePolicy() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: CreatePolicyData) => aclApi.createPolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.policies() })
    },
    onError: handleError,
  })
}

export function useUpdatePolicy(id: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.update,
  })

  return useMutation({
    mutationFn: (data: UpdatePolicyData) => aclApi.updatePolicy(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.policyDetail(id) })
      queryClient.invalidateQueries({ queryKey: aclKeys.policies() })
    },
    onError: handleError,
  })
}

export function useDeletePolicy() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: (id: string) => aclApi.deletePolicy(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.policies() })
    },
    onError: handleError,
  })
}

// ============================================================================
// Policy Attribute Rule Mutations
// ============================================================================

export function useCreatePolicyAttrRule(policyId: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: CreatePolicyAttrRuleData) => aclApi.createPolicyAttrRule(policyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.policyAttrRules(policyId) })
    },
    onError: handleError,
  })
}

export function useDeletePolicyAttrRule(policyId: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: (ruleId: string) => aclApi.deletePolicyAttrRule(policyId, ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.policyAttrRules(policyId) })
    },
    onError: handleError,
  })
}

// ============================================================================
// Assignment Queries & Mutations
// ============================================================================

export function useAclAssignments(params?: AclAssignmentListParams) {
  return useQuery({
    queryKey: aclKeys.assignmentList(params),
    queryFn: () => aclApi.listAssignments(params),
  })
}

export function useAclAssignment(id: string) {
  return useQuery({
    queryKey: aclKeys.assignmentDetail(id),
    queryFn: () => aclApi.getAssignment(id),
    enabled: !!id,
  })
}

export function useCreateAssignment() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: CreateAssignmentData) => aclApi.createAssignment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.assignments() })
      // Also invalidate my permissions since assignments may affect current user
      queryClient.invalidateQueries({ queryKey: aclKeys.myPermissions() })
    },
    onError: handleError,
  })
}

export function useUpdateAssignment(id: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.update,
  })

  return useMutation({
    mutationFn: (data: UpdateAssignmentData) => aclApi.updateAssignment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.assignmentDetail(id) })
      queryClient.invalidateQueries({ queryKey: aclKeys.assignments() })
      queryClient.invalidateQueries({ queryKey: aclKeys.myPermissions() })
    },
    onError: handleError,
  })
}

export function useDeleteAssignment() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: (id: string) => aclApi.deleteAssignment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aclKeys.assignments() })
      queryClient.invalidateQueries({ queryKey: aclKeys.myPermissions() })
    },
    onError: handleError,
  })
}

// ============================================================================
// My Permissions
// ============================================================================

export function useMyPermissions() {
  return useQuery({
    queryKey: aclKeys.myPermissions(),
    queryFn: () => aclApi.getMyPermissions(),
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: false,
  })
}

/**
 * Hook to check if the current user has a specific permission.
 * Returns { can: boolean, isLoading: boolean }.
 */
export function useCanAccess(permission: string) {
  const { data, isLoading } = useMyPermissions()
  const can = data?.permissions?.includes(permission) ?? false
  return { can, isLoading }
}

/**
 * Hook to check if the current user has any of the given permissions.
 */
export function useCanAccessAny(...permissions: string[]) {
  const { data, isLoading } = useMyPermissions()
  const can = permissions.some((p) => data?.permissions?.includes(p)) ?? false
  return { can, isLoading }
}

// ============================================================================
// Audit Log
// ============================================================================

export function useAuditLogs(params?: AuditLogListParams) {
  return useQuery({
    queryKey: aclKeys.auditLogList(params),
    queryFn: () => aclApi.listAuditLogs(params),
  })
}
