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
  is_hidden_gem: boolean
  locally_available: boolean
  trailer_key: string | null
  onFeedback: (tmdb_id: number, type: string) => void
}

export default function ResultCard({
  tmdb_id, title, year, media_type, overview, poster_path,
  vote_average, content_rating, runtime, genres, explanation,
  is_hidden_gem, locally_available, trailer_key, onFeedback,
}: ResultCardProps) {
  const posterUrl = poster_path
    ? `https://image.tmdb.org/t/p/w342${poster_path}`
    : null

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden flex gap-0">
      {/* Poster */}
      <div className="w-28 min-w-28 bg-gray-800 flex-shrink-0">
        {posterUrl ? (
          <img src={posterUrl} alt={title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-600 text-xs p-2 text-center">
            No Poster
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 p-4 min-w-0 space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-white leading-tight">{title}</h3>
            <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5 flex-wrap">
              {year && <span>{year}</span>}
              <span className="bg-gray-800 px-1.5 py-0.5 rounded text-[10px] uppercase">
                {media_type}
              </span>
              {content_rating && (
                <span className="bg-gray-800 px-1.5 py-0.5 rounded text-[10px]">
                  {content_rating}
                </span>
              )}
              {runtime && <span>{runtime}m</span>}
            </div>
          </div>
          {vote_average && (
            <div className="text-sm font-medium text-amber-400 whitespace-nowrap">
              {vote_average.toFixed(1)}
            </div>
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5">
          {genres.slice(0, 3).map((g) => (
            <span key={g} className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
              {g}
            </span>
          ))}
          {is_hidden_gem && (
            <span className="text-[10px] bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded-full">
              Hidden Gem
            </span>
          )}
          {locally_available && (
            <span className="text-[10px] bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full">
              In Library
            </span>
          )}
        </div>

        {/* Overview */}
        {overview && (
          <p className="text-xs text-gray-400 line-clamp-2">{overview}</p>
        )}

        {/* Explanation */}
        <p className="text-xs text-violet-400 italic">{explanation}</p>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={() => onFeedback(tmdb_id, 'thumbs_up')}
            className="text-lg hover:scale-125 transition-transform" title="Like"
          >
            👍
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'thumbs_down')}
            className="text-lg hover:scale-125 transition-transform" title="Dislike"
          >
            👎
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'save')}
            className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1 rounded-full transition-colors"
          >
            Save
          </button>
          <button
            onClick={() => onFeedback(tmdb_id, 'watched')}
            className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1 rounded-full transition-colors"
          >
            Watched
          </button>
          {trailer_key && (
            <a
              href={`https://www.youtube.com/watch?v=${trailer_key}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-red-900 hover:bg-red-800 text-red-200 px-3 py-1 rounded-full transition-colors ml-auto"
            >
              Trailer
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
