import { useState, useEffect } from 'react'
import { useToast, ToastContainer } from '../components/Toast'

interface SourceStatus {
  status: string
  detail?: string
}

interface SystemStatus {
  timestamp: string
  stats: {
    titles: number
    users: number
    feedback: number
    watch_history: number
    watchlist: number
    local_availability: number
  }
  sources: Record<string, SourceStatus>
}

interface AdminUser {
  id: number
  display_name: string
  avatar_url: string | null
  is_admin: boolean
  is_active: boolean
  created_at: string | null
}

interface AdminProps {
  onBack: () => void
}

const AVATAR_COLORS = [
  'from-amber-500 to-orange-600', 'from-blue-500 to-indigo-600', 'from-emerald-500 to-teal-600', 'from-rose-500 to-pink-600', 'from-cyan-500 to-sky-600',
]

const STAT_ICONS: Record<string, string> = {
  titles: 'M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z',
  users: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  feedback: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
  watch_history: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  watchlist: 'M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z',
  local_availability: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
}

const STAT_COLORS: Record<string, string> = {
  titles: 'text-amber-400',
  users: 'text-blue-400',
  feedback: 'text-rose-400',
  watch_history: 'text-emerald-400',
  watchlist: 'text-purple-400',
  local_availability: 'text-cyan-400',
}

export default function Admin({ onBack }: AdminProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)

  const [users, setUsers] = useState<AdminUser[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editAdmin, setEditAdmin] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [userError, setUserError] = useState<string | null>(null)

  const [aiProvider, setAiProvider] = useState<string>('')
  const [aiStatus, setAiStatus] = useState<string>('')
  const [aiSwitching, setAiSwitching] = useState(false)

  const [languages, setLanguages] = useState<{ id?: number; code: string; name: string }[]>([])
  const [langSaving, setLangSaving] = useState(false)
  const [newLangCode, setNewLangCode] = useState('')
  const [newLangName, setNewLangName] = useState('')

  const [apiKeys, setApiKeys] = useState<{ name: string; label: string; masked: string; configured: boolean }[]>([])
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editKeyValue, setEditKeyValue] = useState('')
  const [keySaving, setKeySaving] = useState(false)
  const toast = useToast()

  const fetchAiSettings = async () => {
    try {
      const resp = await fetch('/api/admin/ai-settings')
      const data = await resp.json()
      setAiProvider(data.provider || '')
      setAiStatus(data.status || 'unknown')
    } catch {
      toast.error('Failed to load AI settings')
    }
  }

  const fetchApiKeys = async () => {
    try {
      const resp = await fetch('/api/admin/api-keys')
      const data = await resp.json()
      setApiKeys(data.keys || [])
    } catch {
      toast.error('Failed to load API keys')
    }
  }

  const saveApiKey = async (name: string, value: string) => {
    setKeySaving(true)
    try {
      const resp = await fetch('/api/admin/api-keys', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys: { [name]: value } }),
      })
      const data = await resp.json()
      if (data.status === 'ok') {
        toast.success('API key updated')
        setEditingKey(null)
        setEditKeyValue('')
        fetchApiKeys()
        fetchStatus()
        fetchAiSettings()
      } else {
        toast.error(data.detail || 'Failed to update key')
      }
    } catch {
      toast.error('Failed to update API key')
    } finally {
      setKeySaving(false)
    }
  }

  const switchAiProvider = async (provider: string) => {
    setAiSwitching(true)
    try {
      const resp = await fetch('/api/admin/ai-settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })
      const data = await resp.json()
      if (data.status === 'ok') {
        setAiProvider(provider)
        fetchAiSettings()
        toast.success(`Switched to ${provider}`)
      } else {
        toast.error(`AI switch failed: ${data.detail}`)
      }
    } catch {
      toast.error('AI provider switch failed')
    } finally {
      setAiSwitching(false)
    }
  }

  const fetchLanguages = async () => {
    try {
      const resp = await fetch('/api/admin/languages')
      const data = await resp.json()
      setLanguages(data.map((l: { language_code: string; language_name: string }) => ({
        code: l.language_code, name: l.language_name,
      })))
    } catch {
      toast.error('Failed to load languages')
    }
  }

  const saveLanguages = async (langs: { code: string; name: string }[]) => {
    setLangSaving(true)
    try {
      await fetch('/api/admin/languages', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ languages: langs }),
      })
      setLanguages(langs)
      toast.success('Language preferences saved')
    } catch {
      toast.error('Failed to save language preferences')
    } finally {
      setLangSaving(false)
    }
  }

  const addLanguage = () => {
    if (!newLangCode.trim() || !newLangName.trim() || languages.length >= 5) return
    const updated = [...languages, { code: newLangCode.trim().toLowerCase(), name: newLangName.trim() }]
    setNewLangCode('')
    setNewLangName('')
    saveLanguages(updated)
  }

  const removeLanguage = (index: number) => {
    const updated = languages.filter((_, i) => i !== index)
    saveLanguages(updated)
  }

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/admin/status')
      setStatus(await resp.json())
    } catch {
      toast.error('Failed to load system status')
    } finally {
      setLoading(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const resp = await fetch('/api/users')
      setUsers(await resp.json())
    } catch {
      toast.error('Failed to load users')
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchUsers()
    fetchAiSettings()
    fetchLanguages()
    fetchApiKeys()
  }, [])

  const runAction = async (endpoint: string, label: string) => {
    setActionLoading(label)
    setActionResult(null)
    try {
      const resp = await fetch(`/api/admin/${endpoint}`, { method: 'POST' })
      const data = await resp.json()
      const detail = data.imported != null ? `${data.imported} items` : data.status || 'done'
      setActionResult(`${label}: ${detail}`)
      toast.success(`${label} completed`)
      fetchStatus()
    } catch {
      setActionResult(`${label}: failed`)
      toast.error(`${label} failed`)
    } finally {
      setActionLoading(null)
    }
  }

  const startEdit = (user: AdminUser) => {
    setEditingId(user.id)
    setEditName(user.display_name)
    setEditAdmin(user.is_admin)
    setUserError(null)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setUserError(null)
  }

  const saveEdit = async () => {
    if (!editingId || !editName.trim()) return
    setUserError(null)
    try {
      const resp = await fetch(`/api/users/${editingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: editName.trim(), is_admin: editAdmin }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Update failed' }))
        setUserError(err.detail)
        return
      }
      setEditingId(null)
      fetchUsers()
      fetchStatus()
    } catch {
      setUserError('Update failed')
    }
  }

  const confirmDelete = async (userId: number) => {
    setUserError(null)
    try {
      const resp = await fetch(`/api/users/${userId}`, { method: 'DELETE' })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Delete failed' }))
        setUserError(err.detail)
        setDeletingId(null)
        return
      }
      setDeletingId(null)
      fetchUsers()
      fetchStatus()
    } catch {
      setUserError('Delete failed')
      setDeletingId(null)
    }
  }

  const statusColor = (s: string) => {
    if (s === 'connected' || s === 'configured') return 'text-emerald-400'
    if (s === 'not_configured') return 'text-yellow-400'
    return 'text-red-400'
  }

  const statusDot = (s: string) => {
    if (s === 'connected' || s === 'configured') return 'bg-emerald-500 shadow-emerald-500/30'
    if (s === 'not_configured') return 'bg-yellow-500 shadow-yellow-500/30'
    return 'bg-red-500 shadow-red-500/30'
  }

  return (
    <div className="min-h-screen cinema-bg text-white">
      <header className="cinema-header sticky top-0 z-20 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-semibold">Dashboard</h1>
            <p className="text-[10px] text-gray-600">System overview and management</p>
          </div>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-6 relative z-10">
        {loading && !status && (
          <div className="grid grid-cols-2 gap-3">
            {[1,2,3,4].map(i => <div key={i} className="shimmer h-24 rounded-xl" />)}
          </div>
        )}

        {status && (
          <>
            {/* Stats Grid */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Database Stats</h2>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(status.stats).map(([key, val]) => (
                  <div key={key} className="stat-card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <svg className={`w-5 h-5 ${STAT_COLORS[key] || 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={STAT_ICONS[key] || 'M4 6h16M4 12h16M4 18h16'} />
                      </svg>
                    </div>
                    <p className="text-2xl font-bold">{val.toLocaleString()}</p>
                    <p className="text-xs text-gray-500 capitalize mt-0.5">{key.replace(/_/g, ' ')}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Source Health */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Source Health</h2>
              <div className="card divide-y divide-white/6">
                {Object.entries(status.sources).map(([name, src]) => (
                  <div key={name} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full shadow-lg ${statusDot(src.status)}`} />
                      <span className="text-sm capitalize">{name}</span>
                    </div>
                    <span className={`text-xs font-medium ${statusColor(src.status)}`}>
                      {src.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* User Management */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Users</h2>
              {userError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2 text-sm text-red-300 mb-3">
                  {userError}
                </div>
              )}
              <div className="card divide-y divide-white/6">
                {users.map((user, i) => (
                  <div key={user.id} className="px-4 py-3">
                    {editingId === user.id ? (
                      <div className="space-y-3">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          maxLength={20}
                          className="w-full cinema-input text-white rounded-xl px-3 py-2 text-sm"
                          autoFocus
                          onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
                        />
                        <label className="flex items-center gap-2 text-sm text-gray-400">
                          <input
                            type="checkbox"
                            checked={editAdmin}
                            onChange={(e) => setEditAdmin(e.target.checked)}
                            className="w-4 h-4 rounded accent-amber-500"
                          />
                          Admin
                        </label>
                        <div className="flex gap-2">
                          <button onClick={saveEdit} className="btn-gold text-xs px-3 py-1.5">Save</button>
                          <button onClick={cancelEdit} className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 rounded-xl px-3 py-1.5 transition-colors">Cancel</button>
                        </div>
                      </div>
                    ) : deletingId === user.id ? (
                      <div className="space-y-2">
                        <p className="text-sm text-red-400">
                          Delete <strong>{user.display_name}</strong>? All their data will be removed.
                        </p>
                        <div className="flex gap-2">
                          <button onClick={() => confirmDelete(user.id)} className="text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl px-3 py-1.5 transition-colors">Delete</button>
                          <button onClick={() => setDeletingId(null)} className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 rounded-xl px-3 py-1.5 transition-colors">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${AVATAR_COLORS[i % AVATAR_COLORS.length]} flex items-center justify-center text-xs font-bold flex-shrink-0`}>
                          {user.display_name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{user.display_name}</p>
                          {user.is_admin && (
                            <span className="text-[10px] text-amber-500 uppercase tracking-wider">Admin</span>
                          )}
                        </div>
                        <div className="flex gap-1.5 flex-shrink-0">
                          <button onClick={() => startEdit(user)} className="text-xs text-gray-500 hover:text-white px-2 py-1 transition-colors">Edit</button>
                          <button onClick={() => { setDeletingId(user.id); setUserError(null) }} className="text-xs text-gray-500 hover:text-red-400 px-2 py-1 transition-colors">Delete</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* Actions */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Actions</h2>
              <div className="space-y-2">
                {[
                  { endpoint: 'refresh-metadata', label: 'Refresh Metadata', desc: 'Update titles from TMDB', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
                  { endpoint: 'sync/jellyfin', label: 'Jellyfin Sync', desc: 'Sync local library', icon: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' },
                  { endpoint: 'sync/trakt', label: 'Trakt Sync', desc: 'Sync all users history', icon: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5' },
                ].map((action) => (
                  <button
                    key={action.label}
                    onClick={() => runAction(action.endpoint, action.label)}
                    disabled={!!actionLoading}
                    className="w-full card-interactive flex items-center gap-3 px-4 py-3 text-left disabled:opacity-50"
                  >
                    <div className="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4.5 h-4.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d={action.icon} />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">
                        {actionLoading === action.label ? `${action.label}...` : action.label}
                      </p>
                      <p className="text-xs text-gray-600">{action.desc}</p>
                    </div>
                    <svg className="w-4 h-4 text-gray-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))}
              </div>
            </section>

            {/* AI Provider */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">AI Provider</h2>
              <div className="card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Current</span>
                  <span className={`text-sm font-medium ${aiStatus === 'connected' ? 'text-emerald-400' : aiStatus === 'not_configured' ? 'text-yellow-400' : 'text-red-400'}`}>
                    {aiProvider || 'none'} ({aiStatus})
                  </span>
                </div>
                <div className="flex gap-2">
                  {['openai', 'anthropic', 'google'].map((p) => (
                    <button
                      key={p}
                      onClick={() => switchAiProvider(p)}
                      disabled={aiSwitching || aiProvider === p}
                      className={`flex-1 text-xs rounded-xl px-3 py-2.5 transition-all border font-medium ${
                        aiProvider === p
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-white/4 text-gray-400 border-white/8 hover:bg-white/8 hover:text-white'
                      } disabled:opacity-50`}
                    >
                      {p === 'openai' ? 'OpenAI' : p === 'anthropic' ? 'Anthropic' : 'Google'}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* API Keys */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">API Keys</h2>
              <div className="card divide-y divide-white/6">
                {apiKeys.map((key) => (
                  <div key={key.name} className="px-4 py-3">
                    {editingKey === key.name ? (
                      <div className="space-y-2">
                        <p className="text-sm font-medium">{key.label}</p>
                        <input
                          type="text"
                          value={editKeyValue}
                          onChange={(e) => setEditKeyValue(e.target.value)}
                          placeholder={`Enter new ${key.label}`}
                          autoFocus
                          className="w-full cinema-input text-white rounded-xl px-3 py-2 text-xs font-mono"
                          onKeyDown={(e) => e.key === 'Enter' && editKeyValue.trim() && saveApiKey(key.name, editKeyValue.trim())}
                        />
                        <div className="flex gap-2">
                          <button onClick={() => saveApiKey(key.name, editKeyValue.trim())} disabled={keySaving || !editKeyValue.trim()} className="btn-gold text-xs px-3 py-1.5 disabled:opacity-50">{keySaving ? 'Saving...' : 'Save'}</button>
                          <button onClick={() => { setEditingKey(null); setEditKeyValue('') }} className="text-xs bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 rounded-xl px-3 py-1.5 transition-colors">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 shadow-lg ${key.configured ? 'bg-emerald-400 shadow-emerald-400/30' : 'bg-gray-600'}`} />
                          <span className="text-sm truncate">{key.label}</span>
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className="text-xs text-gray-600 font-mono">
                            {key.configured ? key.masked : 'Not set'}
                          </span>
                          <button onClick={() => { setEditingKey(key.name); setEditKeyValue('') }} className="text-xs text-gray-500 hover:text-amber-400 transition-colors">Edit</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* Language Preferences */}
            <section>
              <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Language Preferences</h2>
              <div className="card p-4 space-y-3">
                <p className="text-xs text-gray-600">
                  Up to 5 languages. Titles not matching any will be filtered out.
                </p>
                {languages.length > 0 && (
                  <div className="space-y-1.5">
                    {languages.map((lang, i) => (
                      <div key={i} className="flex items-center justify-between bg-white/4 border border-white/6 rounded-xl px-3 py-2">
                        <span className="text-sm">
                          <span className="text-amber-500 font-mono mr-2">{lang.code}</span>
                          {lang.name}
                        </span>
                        <button onClick={() => removeLanguage(i)} disabled={langSaving} className="text-xs text-gray-600 hover:text-red-400 transition-colors disabled:opacity-50">Remove</button>
                      </div>
                    ))}
                  </div>
                )}
                {languages.length === 0 && (
                  <p className="text-xs text-gray-600 italic">No language preferences set (all languages accepted)</p>
                )}
                {languages.length < 5 && (
                  <div className="flex gap-2">
                    <input type="text" value={newLangCode} onChange={(e) => setNewLangCode(e.target.value)} placeholder="Code (e.g. en)" maxLength={5} className="w-20 cinema-input text-white rounded-xl px-2 py-1.5 text-xs" />
                    <input type="text" value={newLangName} onChange={(e) => setNewLangName(e.target.value)} placeholder="Language name" maxLength={50} className="flex-1 cinema-input text-white rounded-xl px-2 py-1.5 text-xs" onKeyDown={(e) => e.key === 'Enter' && addLanguage()} />
                    <button onClick={addLanguage} disabled={langSaving || !newLangCode.trim() || !newLangName.trim()} className="btn-gold text-xs px-3 py-1.5 disabled:opacity-50">Add</button>
                  </div>
                )}
              </div>
            </section>

            {/* Action result */}
            {actionResult && (
              <div className="card px-4 py-3 text-xs text-gray-400 font-mono break-all">
                {actionResult}
              </div>
            )}

            <p className="text-xs text-gray-700 text-center">
              Last checked: {new Date(status.timestamp).toLocaleString()}
            </p>
          </>
        )}
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
