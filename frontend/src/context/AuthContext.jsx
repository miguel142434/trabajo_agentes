import { createContext, useContext, useEffect, useSyncExternalStore } from 'react'
import { authService } from '../services/authService'

const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const session = useSyncExternalStore(authService.subscribe, authService.snapshot)
  useEffect(() => { authService.initialize() }, [])
  return <AuthContext.Provider value={{ ...session, login: () => authService.login(), logout: () => authService.logout() }}>
    {children}
  </AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
