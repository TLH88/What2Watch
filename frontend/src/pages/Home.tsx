import { useUser } from '../context/UserContext'

const actions = [
  { label: 'Find a Movie', icon: '🎬', path: '/discover?type=movie' },
  { label: 'Find a TV Show', icon: '📺', path: '/discover?type=tv' },
  { label: 'Find Something for Us', icon: '👥', path: '/discover?type=group' },
  { label: 'Help Me Remember a Title', icon: '🤔', path: '/recall' },
]

export default function Home() {
  const { currentUser, switchUser } = useUser()

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
              className="flex items-center gap-4 bg-gray-900 hover:bg-gray-800 rounded-xl px-5 py-4 text-left transition-colors"
            >
              <span className="text-2xl">{action.icon}</span>
              <span className="text-lg">{action.label}</span>
            </button>
          ))}
        </div>

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
