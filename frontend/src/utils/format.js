/** Display formatting helpers. */

export function formatViewCount(count) {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M views`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K views`
  return `${count} views`
}

export function formatDuration(minutes) {
  if (minutes < 60) return `${minutes.toFixed(0)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

export function scoreColor(score) {
  if (score >= 0.8) return 'text-emerald-600'
  if (score >= 0.6) return 'text-amber-600'
  return 'text-rose-600'
}

export function scoreBg(score) {
  if (score >= 0.8) return 'bg-emerald-500'
  if (score >= 0.6) return 'bg-amber-500'
  return 'bg-rose-500'
}
