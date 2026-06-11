import { useRef, useState, useCallback } from 'react'
import Header from './components/Header'
import PersonaForm from './components/PersonaForm'
import AgentProgress from './components/AgentProgress'
import CurriculumView from './components/CurriculumView'
import EmptyState from './components/EmptyState'
import { streamCurriculum } from './api/client'
import { APP_NAME, AI_NAME } from './constants/brand'

export default function App() {
  const [activePersona, setActivePersona] = useState(null)
  const [curriculum, setCurriculum] = useState(null)
  const [evalResult, setEvalResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [progressEvents, setProgressEvents] = useState([])
  const [error, setError] = useState(null)
  const [backendOnline, setBackendOnline] = useState(null)
  const abortRef = useRef(null)

  const handleBackendStatus = useCallback((online) => {
    setBackendOnline(online)
  }, [])

  function handleSubmit(persona, options = {}) {
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setActivePersona(persona)
    setCurriculum(null)
    setEvalResult(null)
    setProgressEvents([])
    setError(null)
    setIsLoading(true)

    streamCurriculum(
      persona,
      (event) => setProgressEvents((prev) => [...prev, event]),
      (result) => {
        setCurriculum(result)
        setIsLoading(false)
        abortRef.current = null
      },
      (message) => {
        setError(message)
        setIsLoading(false)
        abortRef.current = null
      },
      { signal: controller.signal, personaId: options.personaId ?? null }
    )
  }

  return (
    <div className="min-h-screen relative overflow-x-hidden">
      {/* Ambient background orbs */}
      <div className="fixed inset-0 pointer-events-none -z-10" aria-hidden>
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-violet-400/20 rounded-full blur-3xl" />
        <div className="absolute top-1/3 -right-32 w-80 h-80 bg-teal-400/15 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/3 w-72 h-72 bg-indigo-400/10 rounded-full blur-3xl" />
      </div>

      <Header backendOnline={backendOnline} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-8">
          <aside className="lg:w-[360px] shrink-0">
            <div className="lg:sticky lg:top-[5rem] space-y-4">
              <PersonaForm
                onSubmit={handleSubmit}
                isLoading={isLoading}
                onBackendStatus={handleBackendStatus}
              />
              {!curriculum && !isLoading && (
                <p className="hidden lg:block text-xs text-slate-400 text-center px-4 leading-relaxed">
                  {AI_NAME} uses your persona to find videos you&apos;ll actually finish —
                  not generic playlists.
                </p>
              )}
            </div>
          </aside>

          <main className="flex-1 min-w-0 space-y-5">
            {error && (
              <div className="flex items-start gap-3 p-4 rounded-2xl bg-rose-50/90 border border-rose-100 text-rose-800 text-sm animate-fade-in backdrop-blur-sm">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-rose-200 text-rose-700 flex items-center justify-center text-xs font-bold">
                  !
                </span>
                <div>
                  <p className="font-semibold">{AI_NAME} hit a snag</p>
                  <p className="text-rose-600 mt-0.5">{error}</p>
                </div>
              </div>
            )}

            {progressEvents.length > 0 && (
              <AgentProgress
                progressEvents={progressEvents}
                isComplete={!isLoading && !!curriculum}
              />
            )}

            {curriculum && (
              <CurriculumView
                curriculum={curriculum}
                activePersona={activePersona}
                evalResult={evalResult}
                setEvalResult={setEvalResult}
              />
            )}

            {!isLoading && !curriculum && !error && progressEvents.length === 0 && (
              <EmptyState />
            )}
          </main>
        </div>
      </div>

      <footer className="border-t border-slate-200/50 bg-white/40 backdrop-blur-sm mt-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400">
          <span className="font-display font-semibold text-slate-500">{APP_NAME}</span>
          <span>Your AI learning guide · YouTube + Claude</span>
        </div>
      </footer>
    </div>
  )
}
