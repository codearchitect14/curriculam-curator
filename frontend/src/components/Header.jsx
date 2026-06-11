import Logo from './Logo'
import { APP_NAME, TAGLINE } from '../constants/brand'

export default function Header({ backendOnline }) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/70 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <Logo size="md" glow />
            <div>
              <h1 className="font-display text-base font-bold text-slate-900 leading-tight tracking-tight">
                {APP_NAME}
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">{TAGLINE}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div
              className={`hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs text-slate-500 bg-slate-100/80`}
            >
              <span className="text-violet-600 font-medium">AI</span>
              <span>· learns with you</span>
            </div>
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
                backendOnline === true
                  ? 'bg-emerald-50/80 text-emerald-700 border-emerald-200/80'
                  : backendOnline === false
                    ? 'bg-rose-50/80 text-rose-700 border-rose-200/80'
                    : 'bg-slate-50 text-slate-500 border-slate-200'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  backendOnline === true
                    ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                    : backendOnline === false
                      ? 'bg-rose-500'
                      : 'bg-slate-400 animate-pulse-soft'
                }`}
              />
              {backendOnline === true
                ? 'Ready to help'
                : backendOnline === false
                  ? 'Offline'
                  : 'Connecting…'}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
