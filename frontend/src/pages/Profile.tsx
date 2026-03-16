import { useState, useEffect, useRef } from 'react'
import { useUser } from '../context/UserContext'
import { useToast, ToastContainer } from '../components/Toast'

interface GenrePref {
  genre_id: number
  genre_name: string
  preference: string
}

interface ProfileData {
  id: number
  display_name: string
  avatar_url: string | null
  is_admin: boolean
  onboarding_completed: boolean
  hidden_gem_openness: number
  darkness_tolerance: number
  min_quality_threshold: number
  preferred_runtime_max: number | null
  trakt_connected: boolean
  taste_profile: string | null
  taste_profile_updated_at: string | null
  genre_preferences: GenrePref[]
  movies_watched: number
  shows_watched: number
  watchlist_count: number
  feedback_count: number
}

const ALL_GENRES = [
  'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary',
  'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music',
  'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western',
]

interface ProfileProps {
  onBack: () => void
}

export default function Profile({ onBack }: ProfileProps) {
  const { currentUser } = useUser()
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [genrePrefs, setGenrePrefs] = useState<Record<string, string>>({})
  const [generatingProfile, setGeneratingProfile] = useState(false)
  const [syncingRatings, setSyncingRatings] = useState(false)
  const [syncingHistory, setSyncingHistory] = useState(false)
  const [traktCode, setTraktCode] = useState<{ user_code: string; verification_url: string; device_code: string; interval: number } | null>(null)
  const [traktPolling, setTraktPolling] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const toast = useToast()

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (!currentUser) return
    fetch(`/api/users/${currentUser.id}/profile`)
      .then((r) => r.json())
      .then((data) => {
        setProfile(data)
        const prefs: Record<string, string> = {}
        for (const gp of data.genre_preferences || []) {
          prefs[gp.genre_name.toLowerCase()] = gp.preference
        }
        setGenrePrefs(prefs)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [currentUser])

  const cycleGenre = (genre: string) => {
    const key = genre.toLowerCase()
    const current = genrePrefs[key]
    let next: string | undefined
    if (!current) next = 'like'
    else if (current === 'like') next = 'dislike'
    else next = undefined

    setGenrePrefs((prev) => {
      const updated = { ...prev }
      if (next) updated[key] = next
      else delete updated[key]
      return updated
    })
  }

  const saveGenrePrefs = async () => {
    if (!currentUser) return
    setSaving(true)
    try {
      await fetch(`/api/users/${currentUser.id}/genre-preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: Object.entries(genrePrefs).map(([genre, pref]) => ({
            genre_name: genre,
            preference: pref,
          })),
        }),
      })
      toast.success('Genre preferences saved')
    } catch {
      toast.error('Failed to save genre preferences')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateProfile = async () => {
    if (!currentUser) return
    setGeneratingProfile(true)
    try {
      const resp = await fetch(`/api/users/generate-taste-profile?user_id=${currentUser.id}`, {
        method: 'POST',
      })
      const data = await resp.json()
      if (data.taste_profile) {
        setProfile((prev) => prev ? { ...prev, taste_profile: data.taste_profile, taste_profile_updated_at: new Date().toISOString() } : prev)
        toast.success('Taste profile generated')
      }
    } catch {
      toast.error('Failed to generate profile')
    } finally {
      setGeneratingProfile(false)
    }
  }

  const handleSyncRatings = async () => {
    if (!currentUser) return
    setSyncingRatings(true)
    try {
      const resp = await fetch(`/api/users/sync-trakt-ratings?user_id=${currentUser.id}`, {
        method: 'POST',
      })
      const data = await resp.json()
      toast.success(`Imported ${data.imported} ratings from Trakt`)
      if (data.taste_profile) {
        setProfile((prev) => prev ? { ...prev, taste_profile: data.taste_profile, taste_profile_updated_at: new Date().toISOString(), feedback_count: (prev.feedback_count || 0) + data.imported } : prev)
      }
    } catch {
      toast.error('Failed to sync Trakt ratings')
    } finally {
      setSyncingRatings(false)
    }
  }

  const handleSyncHistory = async () => {
    if (!currentUser) return
    setSyncingHistory(true)
    try {
      const resp = await fetch(`/api/users/sync-trakt-history?user_id=${currentUser.id}`, {
        method: 'POST',
      })
      const data = await resp.json()
      toast.success(`Imported ${data.imported} watch history items from Trakt`)
      const profileResp = await fetch(`/api/users/${currentUser.id}/profile`)
      const profileData = await profileResp.json()
      setProfile(profileData)
    } catch {
      toast.error('Failed to sync Trakt watch history')
    } finally {
      setSyncingHistory(false)
    }
  }

  const handleTraktConnect = async () => {
    if (!currentUser) return
    try {
      const resp = await fetch(`/api/users/trakt/connect?user_id=${currentUser.id}`, { method: 'POST' })
      if (!resp.ok) throw new Error()
      const data = await resp.json()
      setTraktCode(data)
      setTraktPolling(true)

      pollTimerRef.current = setInterval(async () => {
        try {
          const pollResp = await fetch(`/api/users/trakt/poll?user_id=${currentUser.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_code: data.device_code }),
          })
          const pollData = await pollResp.json()

          if (pollData.status === 'connected') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
            setTraktCode(null)
            setTraktPolling(false)
            setProfile((prev) => prev ? { ...prev, trakt_connected: true } : prev)
            toast.success('Trakt connected!')
          } else if (pollData.status === 'expired' || pollData.status === 'denied') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
            setTraktCode(null)
            setTraktPolling(false)
            toast.error('Trakt authorization expired or denied')
          }
        } catch {
          // Network error during poll — keep trying
        }
      }, (data.interval || 5) * 1000)
    } catch {
      toast.error('Failed to start Trakt connection')
    }
  }

  const handleTraktDisconnect = async () => {
    if (!currentUser) return
    setDisconnecting(true)
    try {
      await fetch(`/api/users/trakt/disconnect?user_id=${currentUser.id}`, { method: 'POST' })
      setProfile((prev) => prev ? { ...prev, trakt_connected: false } : prev)
      toast.success('Trakt disconnected')
    } catch {
      toast.error('Failed to disconnect Trakt')
    } finally {
      setDisconnecting(false)
    }
  }

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
          <h1 className="text-lg font-semibold flex-1 text-center pr-5">Profile</h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-6 relative z-10">
        {loading && (
          <div className="flex flex-col items-center py-8 gap-3">
            <div className="shimmer w-20 h-20 rounded-full" />
            <div className="shimmer w-32 h-5 rounded-lg" />
          </div>
        )}

        {profile && (
          <>
            {/* Avatar & Name - Centered */}
            <div className="flex flex-col items-center text-center pt-2">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-3xl font-bold shadow-lg shadow-amber-500/20 ring-4 ring-amber-500/10">
                {profile.display_name.charAt(0).toUpperCase()}
              </div>
              <h2 className="text-xl font-bold mt-3">{profile.display_name}</h2>
              {profile.is_admin && (
                <span className="text-[10px] text-amber-500 uppercase tracking-wider font-medium mt-0.5">Admin</span>
              )}
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="card p-3 text-center">
                <p className="text-xl font-bold text-white">{(profile.movies_watched || 0) + (profile.shows_watched || 0)}</p>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Watched</p>
              </div>
              <div className="card p-3 text-center">
                <p className="text-xl font-bold text-white">{profile.feedback_count || 0}</p>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Reviews</p>
              </div>
              <div className="card p-3 text-center">
                <p className="text-xl font-bold text-white">{profile.watchlist_count}</p>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Watchlist</p>
              </div>
            </div>

            {/* Taste Profile */}
            <section>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Taste Profile</h3>
              <div className="card p-4 space-y-3">
                {profile.taste_profile ? (
                  <>
                    <p className="text-sm text-gray-300 leading-relaxed">{profile.taste_profile}</p>
                    {profile.taste_profile_updated_at && (
                      <p className="text-[10px] text-gray-600">
                        Updated {new Date(profile.taste_profile_updated_at).toLocaleDateString()}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-600 italic">
                    {(profile.feedback_count || 0) > 0
                      ? 'Profile not yet generated. Click below to generate.'
                      : 'Rate some titles or sync your Trakt ratings to build your taste profile.'}
                  </p>
                )}

                <button
                  onClick={handleGenerateProfile}
                  disabled={generatingProfile || syncingRatings}
                  className="btn-gold px-4 py-2 text-xs disabled:opacity-50"
                >
                  {generatingProfile ? 'Generating...' : profile.taste_profile ? 'Regenerate' : 'Generate Profile'}
                </button>
              </div>
            </section>

            {/* Genre Preferences */}
            <section>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Genre Preferences</h3>
              <p className="text-xs text-gray-600 mb-3">
                Tap to cycle: neutral → like → dislike → neutral
              </p>
              <div className="flex flex-wrap gap-2">
                {ALL_GENRES.map((genre) => {
                  const pref = genrePrefs[genre.toLowerCase()]
                  let classes = 'bg-white/5 text-gray-400 border-white/8'
                  if (pref === 'like') classes = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20'
                  if (pref === 'dislike') classes = 'bg-red-500/15 text-red-400 border-red-500/20'
                  return (
                    <button
                      key={genre}
                      onClick={() => cycleGenre(genre)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all hover:scale-105 ${classes}`}
                    >
                      {pref === 'like' && '+ '}
                      {pref === 'dislike' && '- '}
                      {genre}
                    </button>
                  )
                })}
              </div>
              <button
                onClick={saveGenrePrefs}
                disabled={saving}
                className="mt-3 btn-gold px-4 py-2 text-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Genre Preferences'}
              </button>
            </section>

            {/* Integrations */}
            <section>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Integrations</h3>
              <div className="card divide-y divide-white/6">
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-red-500/10 flex items-center justify-center">
                      <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Trakt</p>
                      <p className="text-xs text-gray-600">
                        {profile.trakt_connected ? 'Connected' : 'Not connected'}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      profile.trakt_connected ? 'bg-emerald-500 shadow-lg shadow-emerald-500/30' : 'bg-gray-700'
                    }`}
                  />
                </div>

                {traktCode && (
                  <div className="p-4 space-y-2">
                    <p className="text-xs text-gray-400">
                      Go to{' '}
                      <a
                        href={traktCode.verification_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-amber-400 underline"
                      >
                        {traktCode.verification_url}
                      </a>{' '}
                      and enter:
                    </p>
                    <p className="text-2xl font-mono font-bold text-center tracking-widest text-white py-2">
                      {traktCode.user_code}
                    </p>
                    {traktPolling && (
                      <p className="text-[10px] text-gray-600 text-center">Waiting for authorization...</p>
                    )}
                  </div>
                )}

                <div className="p-4 flex flex-wrap gap-2">
                  {!profile.trakt_connected && !traktCode && (
                    <button
                      onClick={handleTraktConnect}
                      className="btn-gold px-3 py-1.5 text-xs"
                    >
                      Connect Trakt
                    </button>
                  )}
                  {profile.trakt_connected && (
                    <>
                      <button
                        onClick={handleSyncHistory}
                        disabled={syncingHistory || syncingRatings}
                        className="btn-gold px-3 py-1.5 text-xs disabled:opacity-50"
                      >
                        {syncingHistory ? 'Syncing...' : 'Sync Watch History'}
                      </button>
                      <button
                        onClick={handleSyncRatings}
                        disabled={syncingRatings || syncingHistory || generatingProfile}
                        className="btn-gold px-3 py-1.5 text-xs disabled:opacity-50"
                      >
                        {syncingRatings ? 'Syncing...' : 'Sync Ratings'}
                      </button>
                      <button
                        onClick={handleTraktDisconnect}
                        disabled={disconnecting}
                        className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs text-gray-400 transition-colors"
                      >
                        Disconnect
                      </button>
                    </>
                  )}
                </div>
              </div>
            </section>
          </>
        )}
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
