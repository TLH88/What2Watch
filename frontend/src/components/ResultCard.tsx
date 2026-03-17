import { useState } from 'react'

interface ResultCardProps {
  tmdb_id: number
  title: string
  year: string | null
  media_type: string
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
  onFeedback: (tmdb_id: number, type: string) => void
  feedbackGiven?: Set<string>
}

export default function ResultCard({
  tmdb_id, title, year, media_type, overview, poster_path,
  vote_average, content_rating, runtime, genres, explanation,
  confidence, is_hidden_gem, is_curveball, locally_available, trailer_key, onFeedback,
  feedbackGiven,
}: ResultCardProps) {
  const [showTrailer, setShowTrailer] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const thumbsUpGiven = feedbackGiven?.has(`${tmdb_id}-thumbs_up`) ?? false
  const thumbsDownGiven = feedbackGiven?.has(`${tmdb_id}-thumbs_down`) ?? false
  const ratingGiven = thumbsUpGiven || thumbsDownGiven
  const saveGiven = feedbackGiven?.has(`${tmdb_id}-save`) ?? false
  const watchedGiven = feedbackGiven?.has(`${tmdb_id}-watched`) ?? false
  const posterUrl = poster_path
    ? `https://image.tmdb.org/t/p/w342${poster_path}`
    : null

  return (
    <div className="card overflow-hidden flex gap-0">
      {/* Poster */}
      <div className="w-24 min-w-24 sm:w-28 sm:min-w-28 bg-white/3 flex-shrink-0">
        {posterUrl ? (
          <img src={posterUrl} alt={title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-700 text-xs p-2 text-center min-h-36">
            No Poster
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 p-3 sm:p-4 min-w-0 space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-white leading-tight">{title}</h3>
            <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5 flex-wrap">
              {year && <span>{year}</span>}
              <span className="bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded text-[10px] uppercase font-medium">
                {media_type}
              </span>
              {content_rating && (
                <span className="bg-white/8 px-1.5 py-0.5 rounded text-[10px]">
                  {content_rating}
                </span>
              )}
              {runtime && <span>{runtime}m</span>}
              {vote_average && (
                <span className="flex items-center gap-0.5 text-amber-400">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {vote_average.toFixed(1)}
                </span>
              )}
            </div>
          </div>
          {confidence > 0 && (
            <div className="text-right whitespace-nowrap flex-shrink-0">
              <div className="text-xl font-bold text-amber-400">{Math.round(confidence * 100)}%</div>
              <div className="text-[9px] text-gray-600 uppercase tracking-wider">Match</div>
            </div>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5">
          {genres.slice(0, 3).map((g) => (
            <span key={g} className="text-[10px] bg-white/6 text-gray-400 px-2 py-0.5 rounded-full">
              {g}
            </span>
          ))}
          {is_hidden_gem && (
            <span className="text-[10px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
              Hidden Gem
            </span>
          )}
          {is_curveball && (
            <span className="text-[10px] bg-amber-500/15 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium">
              Curveball
            </span>
          )}
          {locally_available && (
            <span className="text-[10px] bg-blue-500/15 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full font-medium">
              In Library
            </span>
          )}
        </div>

        {/* Overview */}
        {overview && (
          <p className={`text-xs text-gray-400 leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>{overview}</p>
        )}

        {/* Explanation */}
        <p className={`text-xs text-amber-400/70 italic leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>{explanation}</p>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[11px] font-medium text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1"
        >
          <svg className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
          {expanded ? 'Show less' : 'Show more'}
        </button>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 pt-1">
          <button
            onClick={() => onFeedback(tmdb_id, 'thumbs_up')}
            disabled={ratingGiven}
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
              thumbsUpGiven
                ? 'bg-emerald-500/20 scale-110'
                : ratingGiven
                  ? 'bg-white/4 opacity-30 cursor-not-allowed'
                  : 'bg-white/5 hover:bg-emerald-500/20 hover:scale-110'
            }`}
            title="Like"
          >
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
            </svg>
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'thumbs_down')}
            disabled={ratingGiven}
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
              thumbsDownGiven
                ? 'bg-red-500/20 scale-110'
                : ratingGiven
                  ? 'bg-white/4 opacity-30 cursor-not-allowed'
                  : 'bg-white/5 hover:bg-red-500/20 hover:scale-110'
            }`}
            title="Dislike"
          >
            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
            </svg>
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'save')}
            disabled={saveGiven}
            className={`text-xs px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 border ${
              saveGiven
                ? 'bg-amber-500/15 text-amber-400 border-amber-500/25 cursor-default'
                : 'bg-white/5 hover:bg-amber-500/10 hover:text-amber-400 hover:border-amber-500/20 border-white/8 text-gray-300'
            }`}
          >
            <svg className="w-3 h-3" fill={saveGiven ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            {saveGiven ? 'Saved' : 'Save'}
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'watched')}
            disabled={watchedGiven}
            className={`text-xs px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 border ${
              watchedGiven
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25 cursor-default'
                : 'bg-white/5 hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/20 border-white/8 text-gray-300'
            }`}
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {watchedGiven ? 'Watched' : 'Watch'}
          </button>
          {trailer_key && (
            <button
              onClick={() => setShowTrailer(true)}
              className="text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 px-2.5 py-1 rounded-lg transition-colors ml-auto flex items-center gap-1"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              Trailer
            </button>
          )}
        </div>
      </div>

      {/* Trailer Modal */}
      {showTrailer && trailer_key && (
        <div
          className="fixed inset-0 bg-black/85 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setShowTrailer(false)}
        >
          <div
            className="relative w-full max-w-3xl aspect-video"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowTrailer(false)}
              className="absolute -top-10 right-0 text-white text-xl hover:text-gray-300 transition-colors w-8 h-8 flex items-center justify-center"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <iframe
              src={`https://www.youtube.com/embed/${trailer_key}?autoplay=1`}
              title={`${title} Trailer`}
              allow="autoplay; encrypted-media"
              allowFullScreen
              className="w-full h-full rounded-xl"
            />
          </div>
        </div>
      )}
    </div>
  )
}
