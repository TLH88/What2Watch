import { useState } from 'react'
import { useUser } from '../context/UserContext'
import { api, User } from '../api/client'

const AVATAR_COLORS = [
  'bg-violet-600', 'bg-blue-600', 'bg-emerald-600', 'bg-amber-600', 'bg-rose-600',
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
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <p className="text-gray-400">Loading...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center px-4">
      <h1 className="text-3xl font-bold mb-2">What2Watch</h1>
      <p className="text-gray-400 mb-8">Who's watching?</p>

      <div className="flex flex-wrap justify-center gap-6 mb-8 max-w-md">
        {users.map((user, i) => (
          <button
            key={user.id}
            onClick={() => selectUser(user)}
            className="flex flex-col items-center gap-2 group"
          >
            <div className={`w-20 h-20 rounded-full ${AVATAR_COLORS[i % AVATAR_COLORS.length]} flex items-center justify-center text-2xl font-bold group-hover:ring-4 ring-white/30 transition-all`}>
              {user.display_name.charAt(0).toUpperCase()}
            </div>
            <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
              {user.display_name}
            </span>
            {user.is_admin && (
              <span className="text-[10px] text-gray-500 -mt-1">Admin</span>
            )}
          </button>
        ))}

        {users.length < 5 && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex flex-col items-center gap-2 group"
          >
            <div className="w-20 h-20 rounded-full border-2 border-dashed border-gray-600 flex items-center justify-center text-3xl text-gray-500 group-hover:border-gray-400 group-hover:text-gray-300 transition-colors">
              +
            </div>
            <span className="text-sm text-gray-500 group-hover:text-gray-300 transition-colors">
              Add User
            </span>
          </button>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center px-4 z-50">
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-sm space-y-4">
            <h2 className="text-xl font-semibold">New User</h2>

            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Display name"
              maxLength={20}
              autoFocus
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-3 outline-none focus:ring-2 ring-violet-500"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />

            <label className="flex items-center gap-3 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="w-4 h-4 rounded"
              />
              Admin user
            </label>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex gap-3">
              <button
                onClick={() => { setShowCreate(false); setNewName(''); setError('') }}
                className="flex-1 py-2.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || creating}
                className="flex-1 py-2.5 rounded-lg bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-50 transition-colors"
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
