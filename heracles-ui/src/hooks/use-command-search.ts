import { useEffect, useState } from 'react'
import { groupsApi, usersApi } from '@/lib/api'
import type { Group, User } from '@/types'

interface CommandSearchResult {
  users: User[]
  groups: Group[]
}

interface CommandSearchState extends CommandSearchResult {
  isLoading: boolean
  error: string | null
}

export function useCommandSearch(query: string): CommandSearchState {
  const [state, setState] = useState<CommandSearchState>({
    users: [],
    groups: [],
    isLoading: false,
    error: null,
  })

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setState((prev) => ({
        ...prev,
        users: [],
        groups: [],
        isLoading: false,
        error: null,
      }))
      return
    }

    let isActive = true
    const timeout = window.setTimeout(async () => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }))
      try {
        const [users, groups] = await Promise.all([
          usersApi.list({ search: trimmed, page_size: 5 }),
          groupsApi.list({ search: trimmed, page_size: 5 }),
        ])
        if (!isActive) return
        setState({
          users: users.users ?? [],
          groups: groups.groups ?? [],
          isLoading: false,
          error: null,
        })
      } catch (error) {
        if (!isActive) return
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Search failed',
        }))
      }
    }, 250)

    return () => {
      isActive = false
      window.clearTimeout(timeout)
    }
  }, [query])

  return state
}
