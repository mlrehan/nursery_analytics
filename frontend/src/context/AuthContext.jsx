import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, tokenStore } from '../api/client'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    if (!tokenStore.access) { setLoading(false); return }
    try {
      const { data } = await api.get('/auth/me')
      setUser(data)
    } catch {
      tokenStore.clear()
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadMe() }, [loadMe])

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login-json', { email, password })
    tokenStore.set(data)
    const me = await api.get('/auth/me')
    setUser(me.data)
    return me.data
  }

  const logout = () => {
    tokenStore.clear()
    setUser(null)
    window.location.href = '/login'
  }

  const refreshUser = useCallback(async () => {
    const { data } = await api.get('/auth/me')
    setUser(data)
    return data
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser, setUser, isAdmin: user?.role?.slug === 'admin' }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
