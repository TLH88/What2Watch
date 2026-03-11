import { useState, useEffect } from 'react'
import { useUser } from '../context/UserContext'

interface Reminder {
  id: number
  tmdb_id: number
  media_type: string
  title: string
  poster_path: string | null
  created_at: string | null
}

const actions = [
  { label: 'Find a Movie', icon: '🎬', page: 'discover', type: 'movie' },
  { label: 'Find a TV Show', icon: '📺', page: 'discover', type: 'tv' },
  { label: 'Find Something for Us', icon: '👥', page: 'discover', type: 'group' },
  { label: 'Help Me Remember a Title', icon: '🤔', page: 'recall', type: undefined },
]

interface HomeProps {
  onNavigate: (page: string, type?: string) => void
}

export default function Home({ onNavigate }: HomeProps) {
  const { currentUser, switchUser } = useUser()
  const [reminders, setReminders] = useState<Reminder[]>([])

  useEffect(() => {
    if (!currentUser) return
    fetch(`/api/reminders?user_id=${currentUser.id}`)
      .then((r) => r.json())
      .then(setReminders)
      .catch(() => {})
  }, [currentUser])

  const handleRate = async (reminder: Reminder, feedback: string) => {
    if (!currentUser) return
    await fetch(`/api/reminders/${reminder.id}/rate?feedback=${feedback}&user_id=${currentUser.id}`, {
      method: 'POST',
    })
    setReminders((prev) => prev.filter((r) => r.id !== reminder.id))
  }

  const handleDismiss = async (reminder: Reminder) => {
    await fetch(`/api/reminders/${reminder.id}/dismiss`, { method: 'POST' })
    setReminders((prev) => prev.filter((r) => r.id !== reminder.id))
  }

  if (!currentUser) return null

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-4 border-b border-gray-800">
        <h1 className="text-xl font-bold">What2Watch</h1>
        <button
          onClick={switchUser}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold">
            {currentUser.display_name.charAt(0).toUpperCase()}
          </div>
          Switch
        </button>
      </header>

      {/* Main */}
      <main className="px-4 py-8 max-w-lg mx-auto">
        <p className="text-gray-400 mb-6">
          Hey {currentUser.display_name}, what are you in the mood for?
        </p>

        <div className="grid grid-cols-1 gap-3">
          {actions.map((action) => (
            <button
              key={action.label}
              onClick={() => onNavigate(action.page, action.type)}
              className="flex items-center gap-4 bg-gray-900 hover:bg-gray-800 rounded-xl px-5 py-4 text-left transition-colors"
            >
              <span className="text-2xl">{action.icon}</span>
              <span className="text-lg">{action.label}</span>
            </button>
          ))}
        </div>

        {/* Pending rating reminders */}
        {reminders.length > 0 && (
          <div className="mt-8 space-y-3">
            <p className="text-sm text-gray-400">Rate something you watched</p>
            {reminders.map((r) => (
              <div
                key={r.id}
                className="flex items-center gap-3 bg-gray-900 rounded-xl p-3"
              >
                {r.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w92${r.poster_path}`}
                    alt={r.title}
                    className="w-10 rounded flex-shrink-0"
                  />
                ) : (
                  <div className="w-10 h-14 bg-gray-800 rounded flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{r.title}</p>
                  <p className="text-xs text-gray-500">{r.media_type}</p>
                </div>
                <div className="flex gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => handleRate(r, 'thumbs_up')}
                    className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-emerald-900 text-sm transition-colors"
                    title="Liked it"
                  >
                    +
                  </button>
                  <button
                    onClick={() => handleRate(r, 'thumbs_down')}
                    className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-red-900 text-sm transition-colors"
                    title="Didn't like it"
                  >
                    -
                  </button>
                  <button
                    onClick={() => handleDismiss(r)}
                    className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs text-gray-500 transition-colors"
                    title="Dismiss"
                  >
                    x
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Watchlist shortcut */}
        <div className="mt-8 flex gap-3">
          <button className="flex-1 bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm text-gray-300 transition-colors">
            Watchlist
          </button>
          <button className="flex-1 bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm text-gray-300 transition-colors">
            Recent Searches
          </button>
        </div>
      </main>
    </div>
  )
}
