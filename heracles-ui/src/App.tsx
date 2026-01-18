import { useEffect } from 'react'
import { AppRouter } from './router'
import { useAuthStore } from '@/stores'

function App() {
  const { isAuthenticated, fetchUser } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser()
    }
  }, [isAuthenticated, fetchUser])

  return <AppRouter />
}

export default App
