import { useState } from 'react'
import { useUser } from '../context/UserContext'
import { api } from '../api/client'

const AVATAR_COLORS = [
  'from-amber-500 to-orange-600',
  'from-blue-500 to-indigo-600',
  'from-emerald-500 to-teal-600',
  'from-rose-500 to-pink-600',
  'from-cyan-500 to-sky-600',
]

export default function ChooseUser() {
  const { users, loading, selectUser, refreshUsers } = useUser()
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    setError('')
    try {
      const user = await api.createUser({ display_name: newName.trim(), is_admin: isAdmin })
      await refreshUsers()
      setShowCreate(false)
      setNewName('')
      setIsAdmin(false)
      selectUser(user)
    } catch (e: any) {
      setError(e.message || 'Failed to create user')
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen cinema-bg text-white flex items-center justify-center">
        <div className="shimmer w-48 h-6 rounded-lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen cinema-bg text-white flex flex-col items-center justify-center px-4 relative z-10">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">What2Watch</h1>
        <p className="text-gray-500 mt-1.5 text-sm">Discover your next cinematic journey</p>
      </div>

      {/* User selection */}
      <div className="card-elevated p-6 w-full max-w-sm">
        <h2 className="text-lg font-semibold text-center mb-1">Welcome Back</h2>
        <p className="text-gray-500 text-sm text-center mb-6">Who's watching?</p>

        <div className="space-y-2">
          {users.map((user, i) => (
            <button
              key={user.id}
              onClick={() => selectUser(user)}
              className="w-full flex items-center gap-3 p-3 rounded-xl transition-all hover:bg-white/5 group"
            >
              <div className={`w-11 h-11 rounded-full bg-gradient-to-br ${AVATAR_COLORS[i % AVATAR_COLORS.length]} flex items-center justify-center text-lg font-bold shadow-lg flex-shrink-0`}>
                {user.display_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 text-left">
                <p className="font-medium text-white group-hover:text-amber-400 transition-colors">
                  {user.display_name}
                </p>
                {user.is_admin && (
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider">Admin</p>
                )}
              </div>
              <svg className="w-5 h-5 text-gray-600 group-hover:text-amber-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          ))}
        </div>

        {users.length < 5 && (
          <>
            <div className="flex items-center gap-3 my-4">
              <div className="flex-1 h-px bg-white/8" />
              <span className="text-[10px] text-gray-600 uppercase tracking-widest">or</span>
              <div className="flex-1 h-px bg-white/8" />
            </div>

            <button
              onClick={() => setShowCreate(true)}
              className="w-full flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed border-white/10 text-gray-500 hover:border-amber-500/30 hover:text-amber-400 transition-all"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <span className="text-sm font-medium">Add New User</span>
            </button>
          </>
        )}
      </div>

      {/* Create user modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center px-4 z-50">
          <div className="card-elevated p-6 w-full max-w-sm space-y-4 animate-fade-in">
            <h2 className="text-xl font-semibold">New User</h2>

            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Display name"
                maxLength={20}
                autoFocus
                className="w-full cinema-input text-white rounded-xl pl-10 pr-4 py-3"
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
            </div>

            <label className="flex items-center gap-3 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="w-4 h-4 rounded accent-amber-500"
              />
              Admin user
            </label>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex gap-3">
              <button
                onClick={() => { setShowCreate(false); setNewName(''); setError('') }}
                className="flex-1 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || creating}
                className="flex-1 py-2.5 rounded-xl btn-gold disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
