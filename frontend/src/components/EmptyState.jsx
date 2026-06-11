import AiCompanion from './AiCompanion'
import Logo from './Logo'
import { IconSparkles, IconUser, IconVideo } from './Icons'
import { AI_NAME } from '../constants/brand'

const STEPS = [
  {
    icon: IconUser,
    title: 'Share your goals',
    desc: 'Tell me your background, what you know, and what you want to learn next.',
  },
  {
    icon: IconSparkles,
    title: 'I search & curate',
    desc: 'I scan YouTube, filter the noise, and pick videos that fit your time and style.',
  },
  {
    icon: IconVideo,
    title: 'Learn with confidence',
    desc: 'Review your path, ask me why I chose each video, and track quality scores.',
  },
]

export default function EmptyState() {
  return (
    <div className="animate-fade-in space-y-5">
      <AiCompanion
        size="lg"
        message="Hey — I'm here to build your perfect learning path."
        submessage="Pick a learner profile on the left (or create your own), then hit Generate. I'll hand-pick YouTube videos tailored to your goals, schedule, and skill level."
      />

      <div className="rounded-2xl border border-slate-200/80 bg-white/80 backdrop-blur-sm shadow-card overflow-hidden">
        <div className="relative px-6 sm:px-10 py-10 sm:py-14 text-center overflow-hidden">
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-violet-400/10 rounded-full blur-3xl pointer-events-none"
            aria-hidden
          />
          <div className="relative animate-float inline-block mb-6">
            <Logo size="xl" glow pulse />
          </div>
          <h2 className="font-display text-2xl sm:text-3xl font-bold text-slate-900 mb-2 tracking-tight">
            Learn smarter, <span className="text-shimmer">not longer</span>
          </h2>
          <p className="text-sm sm:text-base text-slate-500 max-w-lg mx-auto leading-relaxed">
            {AI_NAME} turns hours of YouTube browsing into a focused curriculum —
            so you spend time learning, not searching.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-px bg-gradient-to-r from-violet-100/50 via-slate-100 to-teal-100/50 border-t border-slate-100">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <div key={step.title} className="bg-white/90 px-6 py-5 text-left">
                <div className="flex items-center gap-2 mb-2">
                  <span className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-violet-100 to-teal-50 text-violet-600 border border-violet-100/50">
                    <Icon className="w-4 h-4" />
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Step {i + 1}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1">{step.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{step.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
