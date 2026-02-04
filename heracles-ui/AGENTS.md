# heracles-ui

> React frontend for Heracles identity management

## Version: 0.8.0-beta

## Structure

```
src/
├── App.tsx              # Root component
├── router.tsx           # React Router config
├── config/              # Constants, routes
├── components/          # UI components (shadcn/ui)
├── pages/               # Page components
├── hooks/               # Custom hooks (useUsers, useGroups, etc.)
├── stores/              # Zustand stores (auth, plugin, department)
├── services/            # API client
├── schemas/             # Zod validation
└── lib/                 # Utilities
```

## Tech Stack

- React 18 + TypeScript 5 (strict mode)
- Vite 7 + TailwindCSS v4
- React Query v5 (server state)
- Zustand v5 (UI state)
- React Hook Form + Zod
- shadcn/ui components

## Commands (⚠️ Run in container)

```bash
docker compose --profile full exec ui npm test
docker compose --profile full exec ui npm run lint
docker compose --profile full exec ui npm run build

# Shell
make shell s=ui
```

## Key Patterns

```tsx
// Custom hook with React Query
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/users'),
  })
}

// Zustand store
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}))
```

## Rules

- `strict: true` in tsconfig
- Functional components only
- No `any` types
- React Query for server state
- Zustand for UI state
- Zod for form validation
- No Redux, no Axios
