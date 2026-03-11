import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api, User } from '../api/client'

interface UserContextType {
  users: User[]
  currentUser: User | null
  loading: boolean
  selectUser: (user: User) => void
  switchUser: () => void
  refreshUsers: () => Promise<void>
}

const UserContext = createContext<UserContextType | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([])
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUsers = async () => {
    try {
      const data = await api.getUsers()
      setUsers(data)
    } catch {
      setUsers([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshUsers()
  }, [])

  const selectUser = (user: User) => {
    setCurrentUser(user)
  }

  const switchUser = () => {
    setCurrentUser(null)
  }

  return (
    <UserContext.Provider value={{ users, currentUser, loading, selectUser, switchUser, refreshUsers }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useUser must be used within UserProvider')
  return ctx
}
