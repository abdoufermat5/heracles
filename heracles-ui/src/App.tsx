import { useEffect } from 'react'
import { AppRouter } from './router'
import { useAuthStore, usePluginStore } from '@/stores'

function App() {
  const { fetchUser, isAuthenticated } = useAuthStore()
  const { fetchPlugins, isInitialized: pluginsInitialized } = usePluginStore()

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  // Fetch plugin configs once authenticated
  useEffect(() => {
    if (isAuthenticated && !pluginsInitialized) {
      fetchPlugins()
    }
  }, [isAuthenticated, pluginsInitialized, fetchPlugins])

  return <AppRouter />
}

export default App
