import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { TemplateCreate, TemplateUpdate } from '@/lib/api/templates'
import { templatesApi } from '@/lib/api/templates'
import { useMutationErrorHandler, commonErrorMessages } from './use-mutation-error-handler'

export const templateKeys = {
  all: ['templates'] as const,
  lists: () => [...templateKeys.all, 'list'] as const,
  list: (departmentDn?: string) => [...templateKeys.lists(), departmentDn] as const,
  details: () => [...templateKeys.all, 'detail'] as const,
  detail: (id: string) => [...templateKeys.details(), id] as const,
  pluginFields: (objectType: string) => [...templateKeys.all, 'plugin-fields', objectType] as const,
}

export function useTemplates(departmentDn?: string) {
  return useQuery({
    queryKey: templateKeys.list(departmentDn),
    queryFn: () => templatesApi.list(departmentDn),
  })
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: templateKeys.detail(id),
    queryFn: () => templatesApi.get(id),
    enabled: !!id,
  })
}

export function useTemplatePluginFields(objectType: string = 'user') {
  return useQuery({
    queryKey: templateKeys.pluginFields(objectType),
    queryFn: () => templatesApi.pluginFields(objectType),
  })
}

export function useCreateTemplate() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.create,
  })

  return useMutation({
    mutationFn: (data: TemplateCreate) => templatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
    onError: handleError,
  })
}

export function useUpdateTemplate(id: string) {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.update,
  })

  return useMutation({
    mutationFn: (data: TemplateUpdate) => templatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
    onError: handleError,
  })
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient()
  const handleError = useMutationErrorHandler({
    messages: commonErrorMessages.delete,
  })

  return useMutation({
    mutationFn: (id: string) => templatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.lists() })
    },
    onError: handleError,
  })
}
