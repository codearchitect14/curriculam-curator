import { useState } from 'react'
import { IconCheck, IconChevronDown } from './Icons'
import Logo from './Logo'
import { AI_NAME } from '../constants/brand'

const STEP_LABELS = {
  searching_youtube: 'Searching YouTube',
  filtering: 'Filtering candidates',
  curating: 'Curating your path',
  done: 'Ready for you',
}

const STEP_DESCRIPTIONS = {
  searching_youtube: 'Finding videos that match your goals',
  filtering: 'Removing noise and known-topic overlap',
  curating: 'Selecting the best sequence for your time',
  done: 'Your personalized curriculum is ready',
}

const STEP_ORDER = ['searching_youtube', 'filtering', 'curating', 'done']

function getStepStatus(stepKey, progressEvents) {
  const stepsSeen = new Set(progressEvents.map((e) => e.step))
  const lastEvent = progressEvents[progressEvents.length - 1]
  const currentStep = lastEvent?.step

  if (stepsSeen.has('done')) return 'completed'
  if (stepKey === currentStep) return 'active'
  const stepIndex = STEP_ORDER.indexOf(stepKey)
  const currentIndex = STEP_ORDER.indexOf(currentStep)
  if (currentIndex > stepIndex) return 'completed'
  return 'pending'
}

export default function AgentProgress({ progressEvents, isComplete = false }) {
  const [collapsed, setCollapsed] = useState(false)
  const completedCount = STEP_ORDER.filter(
    (s) => getStepStatus(s, progressEvents) === 'completed'
  ).length
  const progressPct = Math.round((completedCount / STEP_ORDER.length) * 100)

  return (
    <div className="rounded-2xl border border-violet-200/40 bg-white/90 backdrop-blur-sm shadow-card overflow-hidden animate-fade-in">
      <button
        type="button"
        onClick={() => isComplete && setCollapsed(!collapsed)}
        className={`w-full flex items-center justify-between px-5 py-4 ${isComplete ? 'hover:bg-violet-50/30 cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center gap-3">
          <Logo size="sm" glow={!isComplete} pulse={!isComplete} />
          <div className="text-left">
            <h2 className="text-sm font-semibold text-slate-900">
              {isComplete
                ? `Done — here's your learning path`
                : `${AI_NAME} is building your curriculum…`}
            </h2>
            <p className="text-xs text-slate-500">
              {isComplete
                ? 'I hand-picked each video for your goals and schedule'
                : `${progressPct}% · hang tight, this usually takes a minute`}
            </p>
          </div>
        </div>
        {isComplete && (
          <IconChevronDown
            className={`w-4 h-4 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`}
          />
        )}
      </button>

      {!isComplete && (
        <div className="px-5 pb-2">
          <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-500 via-indigo-500 to-teal-500 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {(!collapsed || !isComplete) && (
        <div className="px-5 pb-5">
          <ol className="relative space-y-0">
            {STEP_ORDER.map((stepKey, idx) => {
              const status = getStepStatus(stepKey, progressEvents)
              const event = [...progressEvents].reverse().find((e) => e.step === stepKey)
              const isLast = idx === STEP_ORDER.length - 1

              return (
                <li key={stepKey} className="relative flex gap-4 pb-6 last:pb-0">
                  {!isLast && (
                    <span
                      className={`absolute left-[15px] top-8 w-0.5 h-[calc(100%-16px)] ${
                        status === 'completed'
                          ? 'bg-gradient-to-b from-emerald-400 to-teal-400'
                          : 'bg-slate-200'
                      }`}
                    />
                  )}
                  <span
                    className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-xs font-semibold border-2 ${
                      status === 'completed'
                        ? 'bg-gradient-to-br from-emerald-500 to-teal-500 border-transparent text-white'
                        : status === 'active'
                          ? 'bg-white border-violet-500 text-violet-600 shadow-glow'
                          : 'bg-white border-slate-200 text-slate-400'
                    }`}
                  >
                    {status === 'completed' ? (
                      <IconCheck className="w-3.5 h-3.5" />
                    ) : status === 'active' ? (
                      <span className="w-2.5 h-2.5 bg-violet-500 rounded-full animate-pulse-soft" />
                    ) : (
                      idx + 1
                    )}
                  </span>
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div
                      className={`text-sm font-medium ${
                        status === 'pending' ? 'text-slate-400' : 'text-slate-800'
                      }`}
                    >
                      {STEP_LABELS[stepKey]}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {event?.message || STEP_DESCRIPTIONS[stepKey]}
                    </p>
                    {event?.data && (
                      <div className="flex flex-wrap gap-2 mt-1.5">
                        {event.data.candidates != null && (
                          <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-md bg-slate-100 text-slate-600">
                            {event.data.candidates} candidates
                          </span>
                        )}
                        {event.data.entries != null && (
                          <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-md bg-teal-50 text-teal-700">
                            {event.data.entries} videos for you
                          </span>
                        )}
                        {event.data.queries != null && (
                          <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-md bg-violet-50 text-violet-700">
                            {event.data.queries} searches
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}
