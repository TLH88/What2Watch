import { useState, useEffect } from 'react'
import { useUser } from '../context/UserContext'
import { useToast, ToastContainer } from '../components/Toast'

interface WatchlistItem {
  id: number
  status: string
  added_at: string | null
  tmdb_id: number
  title: string
  media_type: string
  poster_path: string | null
  vote_average: number | null
  overview: string | null
  year: string | null
  runtime: number | null
}

interface WatchlistProps {
  onBack: () => void
}

const STATUS_TABS = [
  { key: 'all', label: 'All' },
  { key: 'saved', label: 'Saved' },
  { key: 'watching', label: 'Watching' },
  { key: 'watched', label: 'Watched' },
]

export default function Watchlist({ onBack }: WatchlistProps) {
  const { currentUser } = useUser()
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all')
  const toast = useToast()

  const fetchWatchlist = async () => {
    if (!currentUser) return
    setLoading(true)
    try {
      const resp = await fetch(`/api/watchlist?user_id=${currentUser.id}`)
      const data = await resp.json()
      setItems(data)
    } catch {
      toast.error('Failed to load watchlist')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWatchlist()
  }, [currentUser])

  const updateStatus = async (itemId: number, newStatus: string) => {
    try {
      await fetch(`/api/watchlist/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      setItems((prev) =>
        prev.map((item) => (item.id === itemId ? { ...item, status: newStatus } : item))
      )
      const labels: Record<string, string> = { watching: 'Marked as watching', watched: 'Marked as watched', saved: 'Moved to saved' }
      toast.success(labels[newStatus] || 'Status updated')
    } catch {
      toast.error('Failed to update status')
    }
  }

  const removeItem = async (itemId: number) => {
    try {
      await fetch(`/api/watchlist/${itemId}`, { method: 'DELETE' })
      setItems((prev) => prev.filter((item) => item.id !== itemId))
      toast.success('Removed from watchlist')
    } catch {
      toast.error('Failed to remove item')
    }
  }

  const filtered = activeTab === 'all' ? items : items.filter((i) => i.status === activeTab)

  if (!currentUser) return null

  return (
    <div className="min-h-screen cinema-bg text-white">
      <header className="cinema-header sticky top-0 z-20 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-3">
          <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex-1 flex items-center gap-2">
            <h1 className="text-lg font-semibold">My Watchlist</h1>
            <span className="text-xs text-gray-600 bg-white/5 px-2 py-0.5 rounded-full">{items.length}</span>
          </div>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto relative z-10">
        <div className="flex gap-2 mb-6">
          {STATUS_TABS.map((tab) => {
            const count = tab.key === 'all' ? items.length : items.filter((i) => i.status === tab.key).length
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                  activeTab === tab.key
                    ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                    : 'bg-white/4 text-gray-400 border-white/8 hover:bg-white/8'
                }`}
              >
                {tab.label} {count > 0 && `(${count})`}
              </button>
            )
          })}
        </div>

        {loading && (
          <div className="space-y-3">
            {[1,2,3].map(i => <div key={i} className="shimmer h-28 rounded-xl" />)}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="text-center py-16">
            <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-white/5 flex items-center justify-center">
              <svg className="w-7 h-7 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </div>
            <p className="text-gray-500 text-sm">
              {activeTab === 'all'
                ? 'Your watchlist is empty. Save titles from search results to see them here.'
                : `No ${activeTab} items.`}
            </p>
          </div>
        )}

        <div className="space-y-3">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="card overflow-hidden flex gap-0"
            >
              <div className="w-20 min-w-20 bg-white/3 flex-shrink-0">
                {item.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w185${item.poster_path}`}
                    alt={item.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full min-h-28 flex items-center justify-center text-gray-700 text-xs">
                    No Poster
                  </div>
                )}
              </div>

              <div className="flex-1 p-3 min-w-0 space-y-2">
                <div>
                  <h3 className="font-semibold text-white text-sm leading-tight">{item.title}</h3>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5">
                    {item.year && <span>{item.year}</span>}
                    <span className="bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded text-[10px] uppercase font-medium">
                      {item.media_type}
                    </span>
                    {item.vote_average && (
                      <span className="flex items-center gap-0.5 text-amber-400">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        {item.vote_average.toFixed(1)}
                      </span>
                    )}
                    {item.runtime && <span>{item.runtime}m</span>}
                  </div>
                </div>

                {item.overview && (
                  <p className="text-xs text-gray-600 line-clamp-2">{item.overview}</p>
                )}

                <div className="flex items-center gap-2 pt-1">
                  {item.status !== 'watching' && (
                    <button
                      onClick={() => updateStatus(item.id, 'watching')}
                      className="text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Watching
                    </button>
                  )}
                  {item.status !== 'watched' && (
                    <button
                      onClick={() => updateStatus(item.id, 'watched')}
                      className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      Watched
                    </button>
                  )}
                  {item.status !== 'saved' && (
                    <button
                      onClick={() => updateStatus(item.id, 'saved')}
                      className="text-xs bg-white/5 hover:bg-white/10 border border-white/8 text-gray-400 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      Save
                    </button>
                  )}
                  <button
                    onClick={() => removeItem(item.id)}
                    className="text-xs text-red-400/70 hover:text-red-400 hover:bg-red-500/10 px-2 py-1 rounded-lg transition-colors ml-auto"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
