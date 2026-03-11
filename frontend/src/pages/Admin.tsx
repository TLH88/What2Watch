import { useState, useEffect } from 'react'

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

interface AdminProps {
  onBack: () => void
}

export default function Admin({ onBack }: AdminProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/admin/status')
      setStatus(await resp.json())
    } catch {
      // Handle silently
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const runAction = async (endpoint: string, label: string) => {
    setActionLoading(label)
    setActionResult(null)
    try {
      const resp = await fetch(`/api/admin/${endpoint}`, { method: 'POST' })
      const data = await resp.json()
      setActionResult(`${label}: ${JSON.stringify(data)}`)
      fetchStatus()
    } catch {
      setActionResult(`${label}: failed`)
    } finally {
      setActionLoading(null)
    }
  }

  const statusColor = (s: string) => {
    if (s === 'connected' || s === 'configured') return 'text-emerald-400'
    if (s === 'not_configured') return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm">
          &larr; Back
        </button>
        <h1 className="text-lg font-semibold">Admin Dashboard</h1>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-6">
        {loading && !status && (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        )}

        {status && (
          <>
            {/* Source Health */}
            <section className="space-y-2">
              <h2 className="text-sm text-gray-400 uppercase tracking-wide">Source Health</h2>
              <div className="bg-gray-900 rounded-xl divide-y divide-gray-800">
                {Object.entries(status.sources).map(([name, src]) => (
                  <div key={name} className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm capitalize">{name}</span>
                    <span className={`text-sm ${statusColor(src.status)}`}>
                      {src.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* Stats */}
            <section className="space-y-2">
              <h2 className="text-sm text-gray-400 uppercase tracking-wide">Database Stats</h2>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(status.stats).map(([key, val]) => (
                  <div key={key} className="bg-gray-900 rounded-xl px-4 py-3">
                    <p className="text-2xl font-bold">{val}</p>
                    <p className="text-xs text-gray-500 capitalize">{key.replace('_', ' ')}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Actions */}
            <section className="space-y-2">
              <h2 className="text-sm text-gray-400 uppercase tracking-wide">Actions</h2>
              <div className="space-y-2">
                <button
                  onClick={() => runAction('refresh-metadata', 'Refresh Metadata')}
                  disabled={!!actionLoading}
                  className="w-full bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm text-left transition-colors disabled:opacity-50"
                >
                  {actionLoading === 'Refresh Metadata' ? 'Refreshing...' : 'Refresh Metadata from TMDB'}
                </button>
                <button
                  onClick={() => runAction('sync/jellyfin', 'Jellyfin Sync')}
                  disabled={!!actionLoading}
                  className="w-full bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm text-left transition-colors disabled:opacity-50"
                >
                  {actionLoading === 'Jellyfin Sync' ? 'Syncing...' : 'Sync Jellyfin Library'}
                </button>
                <button
                  onClick={() => runAction('sync/trakt', 'Trakt Sync')}
                  disabled={!!actionLoading}
                  className="w-full bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm text-left transition-colors disabled:opacity-50"
                >
                  {actionLoading === 'Trakt Sync' ? 'Syncing...' : 'Sync Trakt History (All Users)'}
                </button>
              </div>
            </section>

            {/* Action result */}
            {actionResult && (
              <div className="bg-gray-900 rounded-xl px-4 py-3 text-xs text-gray-400 font-mono break-all">
                {actionResult}
              </div>
            )}

            <p className="text-xs text-gray-600 text-center">
              Last checked: {new Date(status.timestamp).toLocaleString()}
            </p>
          </>
        )}
      </main>
    </div>
  )
}
