import { useState, useEffect } from 'react'
import { useUser } from '../context/UserContext'
import { useToast, ToastContainer } from '../components/Toast'

interface Reminder {
  id: number
  tmdb_id: number
  media_type: string
  title: string
  poster_path: string | null
  created_at: string | null
}

interface RecentSearch {
  query: string
  mediaType: string | null
  genres: string[]
  timestamp: number
  resultCount: number
}

type RatedInfo = { id: number; feedback: string }

const actions = [
  {
    label: 'Movie Recommendations',
    description: 'Tailored cinematic experiences based on your favorite genres and recent watches.',
    buttonText: 'Explore Movies',
    image: '/images/MoviesImage.png',
    page: 'discover',
    type: 'movie',
    badge: 'FEATURED DISCOVERY',
  },
  {
    label: 'TV Series',
    description: 'Your next binge-watch awaits. New episodes and trending seasons.',
    buttonText: 'Browse Shows',
    image: '/images/TVShowImage.png',
    page: 'discover',
    type: 'tv',
  },
  {
    label: 'Group Watch',
    description: 'Find something everyone will enjoy. Perfect for movie nights together.',
    buttonText: 'Find for Us',
    image: '/images/GroupWatchImage.png',
    page: 'discover',
    type: 'group',
  },
  {
    label: 'Remember a Title',
    description: "It's on the tip of your tongue. Describe what you remember and we'll find it.",
    buttonText: 'Help Me Remember',
    image: '/images/RememberTitleImage.png',
    page: 'recall',
    type: undefined,
  },
]

interface HomeProps {
  onNavigate: (page: string, opts?: { type?: string; query?: string; genres?: string[] }) => void
}

export default function Home({ onNavigate }: HomeProps) {
  const { currentUser, switchUser } = useUser()
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([])
  const [showRecent, setShowRecent] = useState(false)
  const [ratedItems, setRatedItems] = useState<RatedInfo[]>([])
  const [activeCard, setActiveCard] = useState(0)
  const toast = useToast()

  useEffect(() => {
    if (!currentUser) return
    fetch(`/api/reminders?user_id=${currentUser.id}`)
      .then((r) => r.json())
      .then(setReminders)
      .catch(() => {})
    const key = `w2w_recent_${currentUser.id}`
    const stored = JSON.parse(localStorage.getItem(key) || '[]')
    setRecentSearches(stored)
  }, [currentUser])

  const handleRate = async (reminder: Reminder, feedback: string) => {
    if (!currentUser) return
    if (ratedItems.some((r) => r.id === reminder.id)) return

    setRatedItems((prev) => [...prev, { id: reminder.id, feedback }])
    try {
      await fetch(`/api/reminders/${reminder.id}/rate?feedback=${feedback}&user_id=${currentUser.id}`, {
        method: 'POST',
      })
    } catch {
      toast.error('Failed to save rating')
    }
    setTimeout(() => {
      setReminders((prev) => prev.filter((r) => r.id !== reminder.id))
      setRatedItems((prev) => prev.filter((r) => r.id !== reminder.id))
    }, 800)
  }

  const handleDismiss = async (reminder: Reminder) => {
    try {
      await fetch(`/api/reminders/${reminder.id}/dismiss`, { method: 'POST' })
      setReminders((prev) => prev.filter((r) => r.id !== reminder.id))
    } catch {
      toast.error('Failed to dismiss reminder')
    }
  }

  if (!currentUser) return null

  return (
    <div className="min-h-screen cinema-bg text-white">
      {/* Header */}
      <header className="cinema-header sticky top-0 z-20 px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('profile')}
              className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-sm font-bold shadow-lg shadow-amber-500/15 hover:shadow-amber-500/25 transition-shadow"
            >
              {currentUser.display_name.charAt(0).toUpperCase()}
            </button>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Welcome back,</p>
              <p className="text-sm font-semibold leading-tight">{currentUser.display_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {currentUser.is_admin && (
              <button
                onClick={() => onNavigate('admin')}
                className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors"
                title="Admin"
              >
                <svg className="w-4.5 h-4.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            )}
            <button
              onClick={switchUser}
              className="w-9 h-9 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors"
              title="Switch user"
            >
              <svg className="w-4.5 h-4.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="px-4 pb-8 max-w-lg mx-auto relative z-10">
        {/* Hero */}
        <div className="pt-6 pb-4">
          <h2 className="text-2xl font-bold leading-tight">What's on your<br />mind?</h2>
          <p className="text-gray-500 text-sm mt-2">Personalized discovery powered by your taste.</p>
        </div>

        {/* Featured Cards */}
        <div className="space-y-4">
          {actions.map((action, i) => (
            <button
              key={action.label}
              onClick={() => onNavigate(action.page, { type: action.type })}
              className="w-full text-left group"
            >
              <div className="card overflow-hidden">
                {/* Image */}
                <div className="relative h-40 overflow-hidden">
                  <img
                    src={action.image}
                    alt={action.label}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none'
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#08080f] via-[#08080f]/40 to-transparent" />
                  {action.badge && (
                    <div className="absolute top-3 left-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider bg-gradient-to-r from-amber-500 to-orange-500 text-white px-2.5 py-1 rounded-md">
                        {action.badge}
                      </span>
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="p-4 -mt-8 relative">
                  <h3 className="text-lg font-bold text-white mb-1">{action.label}</h3>
                  <p className="text-sm text-gray-400 mb-3 line-clamp-2">{action.description}</p>
                  <div className="inline-flex items-center gap-2 btn-gold px-4 py-2 text-sm">
                    {action.buttonText}
                    <svg className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                    </svg>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Pending rating reminders */}
        {reminders.length > 0 && (
          <div className="mt-8 space-y-3">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Rate something you watched</h3>
            {reminders.map((r) => (
              <div
                key={r.id}
                className={`flex items-center gap-3 card p-3 transition-opacity duration-500 ${
                  ratedItems.some((ri) => ri.id === r.id) ? 'opacity-40' : ''
                }`}
              >
                {r.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w92${r.poster_path}`}
                    alt={r.title}
                    className="w-10 rounded-lg flex-shrink-0"
                  />
                ) : (
                  <div className="w-10 h-14 bg-white/5 rounded-lg flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{r.title}</p>
                  <p className="text-xs text-gray-600 capitalize">{r.media_type}</p>
                </div>
                <div className="flex gap-1.5 flex-shrink-0">
                  {(() => {
                    const rated = ratedItems.find((ri) => ri.id === r.id)
                    return (
                      <>
                        <button
                          onClick={() => handleRate(r, 'thumbs_up')}
                          disabled={!!rated}
                          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm transition-all ${
                            rated?.feedback === 'thumbs_up'
                              ? 'bg-emerald-500/20 scale-110'
                              : rated
                                ? 'bg-white/5 opacity-30 cursor-not-allowed'
                                : 'bg-white/5 hover:bg-emerald-500/20 hover:scale-110'
                          }`}
                          title="Liked it"
                        >
                          <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleRate(r, 'thumbs_down')}
                          disabled={!!rated}
                          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm transition-all ${
                            rated?.feedback === 'thumbs_down'
                              ? 'bg-red-500/20 scale-110'
                              : rated
                                ? 'bg-white/5 opacity-30 cursor-not-allowed'
                                : 'bg-white/5 hover:bg-red-500/20 hover:scale-110'
                          }`}
                          title="Didn't like it"
                        >
                          <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                          </svg>
                        </button>
                      </>
                    )
                  })()}
                  <button
                    onClick={() => handleDismiss(r)}
                    className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-xs text-gray-600 transition-colors"
                    title="Dismiss"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-8 flex gap-3">
          <button
            onClick={() => onNavigate('watchlist')}
            className="flex-1 card-interactive flex items-center justify-center gap-2 px-4 py-3 text-sm text-gray-300"
          >
            <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            Watchlist
          </button>
          <button
            onClick={() => setShowRecent(!showRecent)}
            className={`flex-1 rounded-xl px-4 py-3 text-sm transition-colors border flex items-center justify-center gap-2 ${
              showRecent
                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                : 'card-interactive text-gray-300'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Recent {recentSearches.length > 0 && `(${recentSearches.length})`}
          </button>
        </div>

        {/* Recent Searches */}
        {showRecent && (
          <div className="mt-4 space-y-4 animate-fade-in">
            {recentSearches.length === 0 ? (
              <p className="text-sm text-gray-600 text-center py-4">No recent searches</p>
            ) : (
              <>
                {[
                  { key: 'movie', label: 'Movies', icon: 'M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z' },
                  { key: 'tv', label: 'TV Shows', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
                  { key: 'group', label: 'For Us', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' },
                  { key: 'recall', label: 'Remember a Title', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
                  { key: 'other', label: 'General', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
                ].map((group) => {
                  const items = recentSearches.filter((s) => {
                    if (group.key === 'other') return !s.mediaType || !['movie', 'tv', 'group', 'recall'].includes(s.mediaType)
                    return s.mediaType === group.key
                  })
                  if (items.length === 0) return null
                  return (
                    <div key={group.key} className="space-y-2">
                      <p className="text-xs text-gray-600 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d={group.icon} />
                        </svg>
                        {group.label}
                      </p>
                      {items.map((s, i) => (
                        <button
                          key={`${s.query}-${i}`}
                          onClick={() => {
                            if (s.mediaType === 'recall') {
                              onNavigate('recall', { query: s.query })
                            } else {
                              onNavigate('discover', { type: s.mediaType || undefined, query: s.query, genres: s.genres })
                            }
                          }}
                          className="w-full flex items-center gap-3 card-interactive p-3 text-left"
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{s.query}</p>
                            <p className="text-xs text-gray-600">
                              {s.resultCount} results &middot; {new Date(s.timestamp).toLocaleDateString()}
                            </p>
                          </div>
                          <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      ))}
                    </div>
                  )
                })}
              </>
            )}
            {recentSearches.length > 0 && (
              <button
                onClick={() => {
                  if (currentUser) {
                    localStorage.removeItem(`w2w_recent_${currentUser.id}`)
                    setRecentSearches([])
                  }
                }}
                className="w-full py-2 text-xs text-gray-600 hover:text-gray-400 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
        )}
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
