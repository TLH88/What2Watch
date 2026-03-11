import { useState } from 'react'

interface Clues {
  media_type: string | null
  era: string | null
  actors: string[]
  setting: string | null
  country: string | null
  tone: string | null
  is_animated: boolean | null
  keywords: string[]
  plot_details: string[]
}

interface Candidate {
  tmdb_id: number
  media_type: string
  title: string
  year: string | null
  overview: string | null
  poster_path: string | null
  vote_average: number | null
  confidence: number
  match_reasons: string[]
}

interface Question {
  question: string
  options: string[]
  field: string
}

interface RecallProps {
  onBack: () => void
}

export default function Recall({ onBack }: RecallProps) {
  const [description, setDescription] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [clues, setClues] = useState<Clues | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [confirmed, setConfirmed] = useState<Candidate | null>(null)
  const [loading, setLoading] = useState(false)

  const handleStart = async () => {
    if (!description.trim()) return
    setLoading(true)
    setCandidates([])
    setQuestion(null)
    setClues(null)
    setConfirmed(null)
    try {
      const resp = await fetch('/api/recall/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: description.trim() }),
      })
      const data = await resp.json()
      setSessionId(data.session_id)
      setClues(data.clues)
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setCandidates(data.candidates || [])
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
      const resp = await fetch('/api/recall/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, answer }),
      })
      const data = await resp.json()
      setClues(data.clues)
      if (data.status === 'asking' && data.question) {
        setQuestion(data.question)
      } else {
        setCandidates(data.candidates || [])
      }
    } catch {
      // Silently handle
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (candidate: Candidate) => {
    setConfirmed(candidate)
    if (sessionId) {
      await fetch('/api/recall/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, tmdb_id: candidate.tmdb_id }),
      })
    }
  }

  const handleReset = () => {
    setDescription('')
    setSessionId(null)
    setClues(null)
    setQuestion(null)
    setCandidates([])
    setConfirmed(null)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
        <button onClick={onBack} className="text-gray-400 hover:text-white text-sm">
          &larr; Back
        </button>
        <h1 className="text-lg font-semibold">Help Me Remember a Title</h1>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto space-y-6">
        {/* Confirmed result */}
        {confirmed && (
          <div className="space-y-4">
            <div className="bg-emerald-900/30 border border-emerald-800 rounded-xl p-4 text-center">
              <p className="text-emerald-400 text-sm mb-2">Found it!</p>
              <div className="flex items-center gap-4">
                {confirmed.poster_path && (
                  <img
                    src={`https://image.tmdb.org/t/p/w154${confirmed.poster_path}`}
                    alt={confirmed.title}
                    className="w-16 rounded"
                  />
                )}
                <div className="text-left">
                  <h3 className="font-semibold text-lg">{confirmed.title}</h3>
                  <p className="text-gray-400 text-sm">{confirmed.year} &middot; {confirmed.media_type}</p>
                </div>
              </div>
            </div>
            <button
              onClick={handleReset}
              className="w-full py-3 rounded-xl bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
            >
              Search Again
            </button>
          </div>
        )}

        {/* Initial input */}
        {!confirmed && !candidates.length && !question && (
          <>
            <p className="text-gray-400 text-sm">
              Describe everything you remember — actors, plot, scenes, era, anything helps.
            </p>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="I remember this movie from the 90s where there was a guy who..."
              rows={4}
              className="w-full bg-gray-900 text-white rounded-xl px-4 py-3 outline-none focus:ring-2 ring-violet-500 resize-none"
              autoFocus
            />
            <button
              onClick={handleStart}
              disabled={loading || !description.trim()}
              className="w-full py-3 rounded-xl bg-violet-600 text-white font-medium hover:bg-violet-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Searching...' : 'Help Me Remember'}
            </button>
          </>
        )}

        {/* Clue summary */}
        {clues && !confirmed && (clues.keywords.length > 0 || clues.actors.length > 0) && (
          <div className="bg-gray-900 rounded-xl p-3 space-y-1">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Extracted clues</p>
            <div className="flex flex-wrap gap-1.5">
              {clues.media_type && (
                <span className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
                  {clues.media_type}
                </span>
              )}
              {clues.era && (
                <span className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
                  {clues.era}
                </span>
              )}
              {clues.is_animated !== null && (
                <span className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
                  {clues.is_animated ? 'Animated' : 'Live Action'}
                </span>
              )}
              {clues.tone && (
                <span className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
                  {clues.tone}
                </span>
              )}
              {clues.actors.map((a) => (
                <span key={a} className="text-[10px] bg-violet-900 text-violet-300 px-2 py-0.5 rounded-full">
                  {a}
                </span>
              ))}
              {clues.keywords.slice(0, 5).map((kw) => (
                <span key={kw} className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Narrowing question */}
        {question && !confirmed && (
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
        {loading && !question && !confirmed && (
          <div className="text-center py-8 text-gray-400">Searching...</div>
        )}

        {/* Candidates */}
        {candidates.length > 0 && !confirmed && (
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">Is it one of these?</p>
            {candidates.map((c) => (
              <button
                key={c.tmdb_id}
                onClick={() => handleConfirm(c)}
                className="w-full flex items-center gap-3 bg-gray-900 hover:bg-gray-800 rounded-xl p-3 text-left transition-colors"
              >
                {c.poster_path ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w92${c.poster_path}`}
                    alt={c.title}
                    className="w-12 rounded flex-shrink-0"
                  />
                ) : (
                  <div className="w-12 h-16 bg-gray-800 rounded flex-shrink-0" />
                )}
                <div className="min-w-0">
                  <h3 className="font-medium text-sm">{c.title}</h3>
                  <p className="text-xs text-gray-400">
                    {c.year} &middot; {c.media_type}
                    {c.vote_average ? ` · ${c.vote_average.toFixed(1)}` : ''}
                  </p>
                  {c.overview && (
                    <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{c.overview}</p>
                  )}
                  {c.match_reasons.length > 0 && (
                    <p className="text-[10px] text-violet-400 mt-0.5">{c.match_reasons[0]}</p>
                  )}
                </div>
              </button>
            ))}
            <button
              onClick={handleReset}
              className="w-full py-2 text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              None of these — try again
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
