import { useState } from 'react'

interface CollectionPart {
  tmdb_id: number
  title: string
  year: string | null
  poster_path: string | null
  overview: string | null
}

interface CollectionInfo {
  collection_id: number
  name: string
  parts: CollectionPart[]
}

interface CollectionSectionProps {
  collection: CollectionInfo
  currentTmdbId: number
  onView: (tmdbId: number, title: string) => void
  onFeedback: (tmdbId: number, type: string) => void
}

export type { CollectionInfo, CollectionPart }

export default function CollectionSection({
  collection,
  currentTmdbId,
  onView,
  onFeedback,
}: CollectionSectionProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between bg-amber-500/8 hover:bg-amber-500/12 border border-amber-500/15 rounded-xl px-4 py-2.5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span className="text-sm text-amber-400 font-medium">{collection.name}</span>
          <span className="text-[10px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded-full">
            {collection.parts.length} films
          </span>
        </div>
        <svg className={`w-4 h-4 text-amber-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="card rounded-t-none -mt-1 pt-3 px-3 pb-3 space-y-2 animate-fade-in">
          {collection.parts.map((p) => {
            const isCurrent = p.tmdb_id === currentTmdbId
            const posterUrl = p.poster_path
              ? `https://image.tmdb.org/t/p/w92${p.poster_path}`
              : null

            return (
              <div
                key={p.tmdb_id}
                className={`flex items-center gap-3 rounded-lg p-2 transition-colors ${
                  isCurrent
                    ? 'bg-amber-500/10 border border-amber-500/15'
                    : 'bg-white/3 hover:bg-white/6'
                }`}
              >
                {posterUrl ? (
                  <img
                    src={posterUrl}
                    alt={p.title}
                    className="w-10 h-14 rounded object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-10 h-14 bg-white/5 rounded flex-shrink-0 flex items-center justify-center text-gray-700 text-[8px]">
                    N/A
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${isCurrent ? 'text-amber-400' : 'text-white'}`}>
                    {p.title}
                  </p>
                  <p className="text-xs text-gray-600">{p.year}</p>
                </div>
                {isCurrent ? (
                  <span className="text-[10px] text-amber-400 bg-amber-500/15 px-2 py-0.5 rounded-full flex-shrink-0 font-medium">
                    Viewing
                  </span>
                ) : (
                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => onView(p.tmdb_id, p.title)}
                      className="text-[10px] bg-white/5 hover:bg-white/10 border border-white/8 text-gray-300 px-2 py-1 rounded-lg transition-colors"
                    >
                      View
                    </button>
                    <button
                      onClick={() => onFeedback(p.tmdb_id, 'save')}
                      className="text-[10px] bg-white/5 hover:bg-white/10 border border-white/8 text-gray-300 px-2 py-1 rounded-lg transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => onFeedback(p.tmdb_id, 'watched')}
                      className="text-[10px] bg-white/5 hover:bg-white/10 border border-white/8 text-gray-300 px-2 py-1 rounded-lg transition-colors"
                    >
                      Watched
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
