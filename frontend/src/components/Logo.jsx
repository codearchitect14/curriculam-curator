import { APP_SHORT } from '../constants/brand'

const SIZES = {
  sm: { box: 'w-8 h-8', text: 'text-[10px]', radius: 'rounded-xl' },
  md: { box: 'w-10 h-10', text: 'text-xs', radius: 'rounded-xl' },
  lg: { box: 'w-14 h-14', text: 'text-base', radius: 'rounded-2xl' },
  xl: { box: 'w-20 h-20', text: 'text-xl', radius: 'rounded-2xl' },
}

/**
 * CC mark — Curriculum Curator logo.
 */
export default function Logo({ size = 'md', glow = false, pulse = false }) {
  const s = SIZES[size] || SIZES.md

  return (
    <div className={`relative inline-flex ${pulse ? 'animate-logo-pulse' : ''}`}>
      {glow && (
        <div
          className={`absolute inset-0 bg-gradient-to-br from-violet-500/40 to-teal-400/30 blur-xl ${s.radius}`}
          aria-hidden
        />
      )}
      <div
        className={`relative ${s.box} ${s.radius} bg-gradient-to-br from-violet-600 via-indigo-600 to-teal-500 flex items-center justify-center shadow-lg ring-1 ring-white/20`}
      >
        <span className={`${s.text} font-bold text-white tracking-tight select-none`}>
          {APP_SHORT}
        </span>
        <span
          className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-teal-300 shadow-sm"
          aria-hidden
        />
      </div>
    </div>
  )
}
