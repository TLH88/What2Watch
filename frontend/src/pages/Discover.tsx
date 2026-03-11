import { useState } from 'react'
import { useUser } from '../context/UserContext'
import ResultCard from '../components/ResultCard'

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
  is_hidden_gem: boolean
  locally_available: boolean
  trailer_key: string | null
}

const GENRE_CHIPS = [
  'Action', 'Comedy', 'Drama', 'Sci-Fi', 'Thriller',
  'Horror', 'Romance', 'Animation', 'Documentary', 'Mystery',
]

interface DiscoverProps {
  initialType?: string
  onBack: () => void
}

export default function Discover({ initialType, onBack }: DiscoverProps) {
  const { currentUser } = useUser()
  const [query, setQuery] = useState('')
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set())

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
          }),
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
      // Silently handle
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
      }
    } catch {
      // Silently handle
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (tmdb_id: number, type: string) => {
    if (!currentUser) return
    const key = `${tmdb_id}-${type}`
    if (feedbackGiven.has(key)) return

    setFeedbackGiven((prev) => new Set(prev).add(key))
    await fetch(`/api/discover/feedback?user_id=${currentUser.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tmdb_id, feedback: type }),
    })
  }

  const handleNewSearch = () => {
    setQuery('')
    setSelectedGenres([])
    setSessionId(null)
    setQuestion(null)
    setResults([])
    setFeedbackGiven(new Set())
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm">
          &larr; Back
        </button>
        <h1 className="text-lg font-semibold">
          {initialType === 'movie' ? 'Find a Movie' :
           initialType === 'tv' ? 'Find a TV Show' :
           'Discover'}
        </h1>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-6">
        {/* Search input */}
        {!results.length && !question && (
          <>
            <div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you in the mood for?"
                className="w-full bg-gray-900 text-white rounded-xl px-4 py-3 outline-none focus:ring-2 ring-violet-500"
                onKeyDown={(e) => e.key === 'Enter' && handleStart()}
                autoFocus
              />
            </div>

            {/* Genre chips */}
            <div className="flex flex-wrap gap-2">
              {GENRE_CHIPS.map((g) => (
                <button
                  key={g}
                  onClick={() => toggleGenre(g)}
                  className={`text-sm px-3 py-1.5 rounded-full transition-colors ${
                    selectedGenres.includes(g)
                      ? 'bg-violet-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>

            <button
              onClick={handleStart}
              disabled={loading || (!query.trim() && selectedGenres.length === 0)}
              className="w-full py-3 rounded-xl bg-violet-600 text-white font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Searching...' : 'Find Recommendations'}
            </button>
          </>
        )}

        {/* Clarifying question */}
        {question && (
          <div className="space-y-4">
            <p className="text-lg">{question.question}</p>
            <div className="grid grid-cols-2 gap-2">
              {question.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleAnswer(opt)}
                  disabled={loading}
                  className="bg-gray-900 hover:bg-gray-800 rounded-xl px-4 py-3 text-sm transition-colors disabled:opacity-50"
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && !question && (
          <div className="text-center py-12 text-gray-400">
            Finding recommendations...
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-gray-400 text-sm">
                {results.length} recommendation{results.length !== 1 ? 's' : ''}
              </p>
              <button
                onClick={handleNewSearch}
                className="text-sm text-violet-400 hover:text-violet-300"
              >
                New Search
              </button>
            </div>
            {results.map((r) => (
              <ResultCard key={r.tmdb_id} {...r} onFeedback={handleFeedback} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
