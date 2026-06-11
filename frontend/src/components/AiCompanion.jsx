import Logo from './Logo'
import { AI_NAME } from '../constants/brand'

/**
 * AI companion speech bubble — gives the app a personal tutor feel.
 */
export default function AiCompanion({
  message,
  submessage = null,
  size = 'md',
  className = '',
}) {
  return (
    <div className={`flex gap-3 sm:gap-4 ${className}`}>
      <div className="shrink-0 pt-1">
        <Logo size={size} glow pulse />
      </div>
      <div className="relative flex-1 min-w-0">
        <div className="absolute -left-2 top-4 w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-r-[8px] border-r-white hidden sm:block" />
        <div className="rounded-2xl rounded-tl-md bg-white border border-slate-200/80 shadow-card px-4 py-3 sm:px-5 sm:py-4">
          <p className="text-xs font-semibold text-violet-600 mb-1">{AI_NAME}</p>
          <p className="text-sm sm:text-base text-slate-800 leading-relaxed font-medium">
            {message}
          </p>
          {submessage && (
            <p className="text-xs sm:text-sm text-slate-500 mt-2 leading-relaxed">
              {submessage}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
