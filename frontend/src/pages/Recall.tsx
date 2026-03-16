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

interface RecallProps {
  initialQuery?: string
  onBack: () => void
}

export default function Recall({ initialQuery, onBack }: RecallProps) {
  const { currentUser } = useUser()
  const [description, setDescription] = useState(initialQuery || '')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [results, setResults] = useState<Result[]>([])
  const [loading, setLoading] = useState(false)
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set())
  const toast = useToast()

  const handleStart = async () => {
    if (!description.trim() || !currentUser) return
    setLoading(true)
    setResults([])
    setQuestion(null)
    setSessionId(null)
    try {
      const resp = await fetch(`/api/discover/start?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: description.trim(),
          include_watched: true,
        }),
      })
      const data = await resp.json()
      setSessionId(data.session_id)
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setResults(data.results || [])
      }
      if (currentUser) {
        const searchEntry = {
          query: description.trim(),
          mediaType: 'recall',
          genres: [],
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

  const handleCollectionView = async (tmdbId: number, title: string) => {
    if (!currentUser) return
    setLoading(true)
    setResults([])
    setQuestion(null)
    setFeedbackGiven(new Set())
    try {
      const resp = await fetch(`/api/discover/start?user_id=${currentUser.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: title, include_watched: true }),
      })
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

  const handleReset = () => {
    setDescription('')
    setSessionId(null)
    setQuestion(null)
    setResults([])
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
          <h1 className="text-lg font-semibold">Remember a Title</h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-5 relative z-10">
        {results.length === 0 && !question && (
          <>
            <div>
              <h2 className="text-xl font-bold mb-1">What do you remember?</h2>
              <p className="text-gray-500 text-sm">
                Describe everything you can — actors, plot, scenes, era, anything helps.
              </p>
            </div>
            <div className="relative">
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="I remember this movie from the 90s where there was a guy who..."
                rows={4}
                className="w-full cinema-input text-white rounded-xl px-4 py-3 pr-14 resize-none"
                autoFocus
              />
              <VoiceMicButton
                onTranscript={(text) => setDescription(text)}
                disabled={loading}
                className="absolute right-2 bottom-2 w-10 h-10"
              />
            </div>
            <button
              onClick={handleStart}
              disabled={loading || !description.trim()}
              className="w-full py-3 btn-gold flex items-center justify-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? 'Searching...' : 'Help Me Remember'}
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
            <p className="text-gray-500 text-sm">Searching our memory...</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-4 animate-fade-in">
            <p className="text-gray-500 text-sm">Is it one of these?</p>
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
            <button
              onClick={handleReset}
              className="w-full py-2.5 text-sm text-gray-500 hover:text-gray-300 transition-colors card-interactive flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              None of these — try again
            </button>
          </div>
        )}
      </main>
      <ToastContainer toasts={toast.toasts} />
    </div>
  )
}
