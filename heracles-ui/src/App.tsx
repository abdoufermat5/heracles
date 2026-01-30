import { useEffect } from 'react'
import { AppRouter } from './router'
import { useAuthStore } from '@/stores'

function App() {
  const { fetchUser } = useAuthStore()

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  return <AppRouter />
}

export default App
