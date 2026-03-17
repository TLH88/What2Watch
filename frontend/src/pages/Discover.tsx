import { useState } from 'react'
import { useUser } from '../context/UserContext'
import ResultCard from '../components/ResultCard'
import CollectionSection from '../components/CollectionSection'
import type { CollectionInfo } from '../components/CollectionSection'
import VoiceMicButton from '../components/VoiceMicButton'
import { useToast, ToastContainer } from '../components/Toast'

interface Question {
  question: string
  options: string[]
  field: string
}

interface Result {
  tmdb_id: number
  media_type: string
  title: string
  year: string | null
  overview: string | null
  poster_path: string | null
  vote_average: number | null
  content_rating: string | null
  runtime: number | null
  genres: string[]
  explanation: string
  score: number
  confidence: number
  is_hidden_gem: boolean
  is_curveball: boolean
  locally_available: boolean
  trailer_key: string | null
  collection: CollectionInfo | null
}

const GENRE_CHIPS = [
  'Action', 'Comedy', 'Drama', 'Sci-Fi', 'Thriller',
  'Horror', 'Romance', 'Animation', 'Documentary', 'Mystery',
]

interface DiscoverProps {
  initialType?: string
  initialQuery?: string
  initialGenres?: string[]
  onBack: () => void
}

export default function Discover({ initialType, initialQuery, initialGenres, onBack }: DiscoverProps) {
  const { currentUser } = useUser()
  const [query, setQuery] = useState(initialQuery || '')
  const [selectedGenres, setSelectedGenres] = useState<string[]>(initialGenres || [])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [includeWatched, setIncludeWatched] = useState(true)
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set())
  const toast = useToast()

  const toggleGenre = (g: string) => {
    setSelectedGenres((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    )
  }

  const handleStart = async () => {
    if (!query.trim() && selectedGenres.length === 0) return
    if (!currentUser) return

    setLoading(true)
    setResults([])
    setQuestion(null)
    setHasMore(false)
    try {
      const resp = await fetch(
        `/api/discover/start?user_id=${currentUser.id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query.trim() || selectedGenres.join(', '),
            media_type: initialType && initialType !== 'group' ? initialType : null,
            genres: selectedGenres.map((g) => g.toLowerCase()),
            include_watched: includeWatched,
          }),
        }
      )
      const data = await resp.json()
      setSessionId(data.session_id)
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setResults(data.results || [])
        setHasMore(data.has_more || false)
      }
      if (currentUser) {
        const searchEntry = {
          query: query.trim() || selectedGenres.join(', '),
          mediaType: initialType || null,
          genres: selectedGenres,
          timestamp: Date.now(),
          resultCount: data.results?.length || 0,
        }
        const key = `w2w_recent_${currentUser.id}`
        const existing = JSON.parse(localStorage.getItem(key) || '[]')
        const updated = [searchEntry, ...existing.filter((s: { query: string }) => s.query !== searchEntry.query)].slice(0, 20)
        localStorage.setItem(key, JSON.stringify(updated))
      }
    } catch {
      toast.error('Search failed — please try again')
    } finally {
      setLoading(false)
    }
  }

  const handleAnswer = async (answer: string) => {
    if (!sessionId) return
    setLoading(true)
    setQuestion(null)
    try {
      const resp = await fetch('/api/discover/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, answer }),
      })
      const data = await resp.json()
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setResults(data.results || [])
        setHasMore(data.has_more || false)
      }
    } catch {
      toast.error('Failed to process answer')
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (tmdb_id: number, type: string) => {
    if (!currentUser) return
    const key = `${tmdb_id}-${type}`
    if (feedbackGiven.has(key)) return

    setFeedbackGiven((prev) => new Set(prev).add(key))
    try {
      await fetch(`/api/discover/feedback?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tmdb_id, feedback: type }),
      })
      const labels: Record<string, string> = { thumbs_up: 'Liked', thumbs_down: 'Disliked', save: 'Saved to watchlist', watched: 'Marked as watched' }
      toast.success(labels[type] || 'Feedback recorded')
    } catch {
      toast.error('Failed to save feedback')
    }
  }

  const handleCollectionView = async (_tmdbId: number, title: string) => {
    if (!currentUser) return
    setLoading(true)
    setResults([])
    setQuestion(null)
    setFeedbackGiven(new Set())
    try {
      const resp = await fetch(
        `/api/discover/start?user_id=${currentUser.id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: title, include_watched: true }),
        }
      )
      const data = await resp.json()
      setSessionId(data.session_id)
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setResults(data.results || [])
      }
    } catch {
      toast.error('Failed to load title')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadMore = async () => {
    if (!sessionId || loadingMore) return
    setLoadingMore(true)
    try {
      const resp = await fetch('/api/discover/more', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      })
      const data = await resp.json()
      setResults((prev) => [...prev, ...(data.results || [])])
      setHasMore(data.has_more || false)
    } catch {
      toast.error('Failed to load more results')
    } finally {
      setLoadingMore(false)
    }
  }

  const handleNewSearch = () => {
    setQuery('')
    setSelectedGenres([])
    setIncludeWatched(true)
    setSessionId(null)
    setQuestion(null)
    setResults([])
    setHasMore(false)
    setFeedbackGiven(new Set())
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
          <h1 className="text-lg font-semibold">
            {initialType === 'movie' ? 'Find a Movie' :
             initialType === 'tv' ? 'Find a TV Show' :
             initialType === 'group' ? 'Group Watch' :
             'Discover'}
          </h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-5 relative z-10">
        {!results.length && !question && (
          <>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600">
                  <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="What are you in the mood for?"
                  className="w-full cinema-input text-white rounded-xl pl-10 pr-4 py-3"
                  onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                  autoFocus
                />
              </div>
              <VoiceMicButton
                onTranscript={(text) => setQuery(text)}
                disabled={loading}
                className="w-12 h-12 flex-shrink-0"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {GENRE_CHIPS.map((g) => (
                <button
                  key={g}
                  onClick={() => toggleGenre(g)}
                  className={`text-xs px-3 py-1.5 rounded-full transition-all border font-medium ${
                    selectedGenres.includes(g)
                      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30 scale-105'
                      : 'bg-white/4 text-gray-400 border-white/8 hover:bg-white/8'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
              <input
                type="checkbox"
                checked={includeWatched}
                onChange={(e) => setIncludeWatched(e.target.checked)}
                className="rounded accent-amber-500"
              />
              Include previously watched
            </label>

            <button
              onClick={handleStart}
              disabled={loading || (!query.trim() && selectedGenres.length === 0)}
              className="w-full py-3 btn-gold flex items-center justify-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? 'Searching...' : 'Find Recommendations'}
              {!loading && (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              )}
            </button>
          </>
        )}

        {question && (
          <div className="space-y-4 animate-fade-in">
            <p className="text-lg font-medium">{question.question}</p>
            <div className="grid grid-cols-2 gap-2">
              {question.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleAnswer(opt)}
                  disabled={loading}
                  className="card-interactive px-4 py-3 text-sm transition-all disabled:opacity-50"
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && !question && (
          <div className="text-center py-12">
            <div className="w-10 h-10 mx-auto mb-3 rounded-full border-2 border-amber-500/30 border-t-amber-500 animate-spin" />
            <p className="text-gray-500 text-sm">Finding recommendations...</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
              <p className="text-gray-500 text-sm">
                {results.length} recommendation{results.length !== 1 ? 's' : ''}
              </p>
              <button
                onClick={handleNewSearch}
                className="text-sm text-amber-400 hover:text-amber-300 font-medium flex items-center gap-1"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                New Search
              </button>
            </div>
            {results.map((r) => (
              <div key={r.tmdb_id}>
                <ResultCard {...r} onFeedback={handleFeedback} feedbackGiven={feedbackGiven} />
                {r.collection && (
                  <CollectionSection
                    collection={r.collection}
                    currentTmdbId={r.tmdb_id}
                    onView={handleCollectionView}
                    onFeedback={handleFeedback}
                  />
                )}
              </div>
            ))}
            {hasMore && (
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="w-full py-3 mt-2 border border-white/10 rounded-xl text-sm text-gray-300 hover:bg-white/5 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loadingMore ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-gray-500/30 border-t-gray-300 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load More Results'
                )}
              </button>
            )}
          </div>
        )}
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
