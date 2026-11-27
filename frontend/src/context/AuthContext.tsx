import { createContext, useContext, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { setApiUser } from '../services/api'

interface User {
  name: string
  email: string
  initials: string
}

interface AuthContextValue {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY = 'bb_user'

function loadUser(): User | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(loadUser)
  const navigate = useNavigate()

  const login = useCallback(async (email: string, _password: string) => {
    // Derive display name and initials from email until a real auth endpoint exists
    const name = email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    const initials = name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()
    const user: User = { name, email, initials }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    setApiUser(email)
    setUser(user)
    navigate('/', { replace: true })
  }, [navigate])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setApiUser(null)
    setUser(null)
    navigate('/login', { replace: true })
  }, [navigate])

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
