import { useState, useEffect } from 'react'

import { checkHealth, getTestPersonas } from '../api/client'

import { formatDuration } from '../utils/format'

import { AI_NAME } from '../constants/brand'
import Logo from './Logo'
import { IconClock, IconSparkles } from './Icons'



function TagList({ items, variant }) {

  if (!items?.length) return <span className="text-xs text-slate-400">None</span>

  const styles =

    variant === 'known'

      ? 'bg-slate-100 text-slate-600'

      : 'bg-violet-100 text-violet-700'

  return (

    <div className="flex flex-wrap gap-1.5">

      {items.map((item) => (

        <span key={item} className={`px-2 py-0.5 text-xs rounded-md font-medium ${styles}`}>

          {item}

        </span>

      ))}

    </div>

  )

}



function PersonaPreview({ persona }) {

  if (!persona) return null

  const ctx = persona.user_context

  return (

    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3">

      <div>

        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Goal</p>

        <p className="text-sm text-slate-700 leading-relaxed">{persona.goal}</p>

      </div>

      <div className="flex items-center gap-2 text-sm text-slate-600">

        <IconClock className="w-4 h-4 text-slate-400" />

        <span className="font-medium">{formatDuration(persona.time_budget_minutes)}</span>

        <span className="text-slate-400">budget</span>

      </div>

      <div>

        <p className="text-xs font-medium text-slate-400 mb-1.5">Background</p>

        <p className="text-xs text-slate-600">{ctx.background}</p>

      </div>

      <div>

        <p className="text-xs font-medium text-slate-400 mb-1.5">Known</p>

        <TagList items={ctx.known} variant="known" />

      </div>

      <div>

        <p className="text-xs font-medium text-slate-400 mb-1.5">To learn</p>

        <TagList items={ctx.unknown} variant="unknown" />

      </div>

      {ctx.constraints && (

        <div>

          <p className="text-xs font-medium text-slate-400 mb-1">Constraints</p>

          <p className="text-xs text-slate-500 italic">{ctx.constraints}</p>

        </div>

      )}

    </div>

  )

}



const inputClass =

  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-colors disabled:opacity-50 disabled:bg-slate-50'



export default function PersonaForm({ onSubmit, isLoading, onBackendStatus }) {

  const [mode, setMode] = useState('test')

  const [testPersonas, setTestPersonas] = useState([])

  const [selectedId, setSelectedId] = useState('')

  const [loadError, setLoadError] = useState(null)



  const [personaId, setPersonaId] = useState('')

  const [goal, setGoal] = useState('')

  const [timeBudget, setTimeBudget] = useState('120')

  const [background, setBackground] = useState('')

  const [known, setKnown] = useState('')

  const [unknown, setUnknown] = useState('')

  const [constraints, setConstraints] = useState('')



  useEffect(() => {

    checkHealth()

      .then(() => {

        onBackendStatus?.(true)

        return getTestPersonas()

      })

      .then((data) => {

        setTestPersonas(data)

        if (data.length > 0) setSelectedId(data[0].persona_id)

      })

      .catch((err) => {

        onBackendStatus?.(false)

        setLoadError(err.message)

      })

  }, [onBackendStatus])



  const selectedPersona = testPersonas.find((p) => p.persona_id === selectedId)?.persona



  function buildCustomPersona() {

    return {

      persona_id: personaId,

      goal,

      time_budget_minutes: parseInt(timeBudget, 10) || 120,

      user_context: {

        background,

        known: known.split(',').map((s) => s.trim()).filter(Boolean),

        unknown: unknown.split(',').map((s) => s.trim()).filter(Boolean),

        constraints,

      },

    }

  }



  function handleSubmit(e) {

    e.preventDefault()

    if (mode === 'test') {

      const selected = testPersonas.find((p) => p.persona_id === selectedId)

      if (selected) onSubmit(selected.persona, { personaId: selectedId })

    } else {

      onSubmit(buildCustomPersona(), { personaId: null })

    }

  }



  return (

    <div className="rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur-sm shadow-card overflow-hidden">

      <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-br from-violet-50/80 via-white to-teal-50/30">

        <div className="flex items-center gap-3">

          <Logo size="sm" glow />

          <div>

            <h2 className="text-sm font-semibold text-slate-900">Tell me about you</h2>

            <p className="text-xs text-slate-500 mt-0.5">

              {AI_NAME} personalizes every pick to your profile

            </p>

          </div>

        </div>

      </div>



      <div className="p-5">

        <div className="flex p-1 rounded-xl bg-slate-100 mb-5">

          {['test', 'custom'].map((m) => (

            <button

              key={m}

              type="button"

              onClick={() => setMode(m)}

              className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${

                mode === m

                  ? 'bg-white text-slate-900 shadow-sm'

                  : 'text-slate-500 hover:text-slate-700'

              }`}

            >

              {m === 'test' ? 'Test Personas' : 'Custom'}

            </button>

          ))}

        </div>



        {loadError && (

          <div className="mb-4 flex items-start gap-2 text-xs text-rose-700 bg-rose-50 border border-rose-100 p-3 rounded-lg">

            <span className="font-medium shrink-0">Connection error</span>

            <span className="text-rose-600">{loadError}</span>

          </div>

        )}



        <form onSubmit={handleSubmit} className="space-y-4">

          {mode === 'test' ? (

            <>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">

                  Select persona

                </label>

                <select

                  value={selectedId}

                  onChange={(e) => setSelectedId(e.target.value)}

                  className={inputClass}

                  disabled={isLoading}

                >

                  {testPersonas.map((p) => (

                    <option key={p.persona_id} value={p.persona_id}>

                      {p.persona_id.replace(/_/g, ' ')}

                    </option>

                  ))}

                </select>

              </div>

              <PersonaPreview persona={selectedPersona} />

            </>

          ) : (

            <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Persona ID</label>

                <input type="text" value={personaId} onChange={(e) => setPersonaId(e.target.value)} required className={inputClass} placeholder="my_learner" />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Learning goal</label>

                <textarea value={goal} onChange={(e) => setGoal(e.target.value)} required rows={2} className={inputClass} placeholder="What do you want to achieve?" />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Time budget (minutes)</label>

                <input type="number" value={timeBudget} onChange={(e) => setTimeBudget(e.target.value)} required min="1" className={inputClass} />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Background</label>

                <input type="text" value={background} onChange={(e) => setBackground(e.target.value)} required className={inputClass} />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Known topics (comma-separated)</label>

                <input type="text" value={known} onChange={(e) => setKnown(e.target.value)} className={inputClass} />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Topics to learn (comma-separated)</label>

                <input type="text" value={unknown} onChange={(e) => setUnknown(e.target.value)} className={inputClass} />

              </div>

              <div>

                <label className="block text-xs font-medium text-slate-600 mb-1.5">Constraints</label>

                <textarea value={constraints} onChange={(e) => setConstraints(e.target.value)} rows={2} className={inputClass} placeholder="e.g. hands-on only, no theory lectures" />

              </div>

            </div>

          )}



          <button

            type="submit"

            disabled={isLoading || !!loadError}

            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-violet-600 via-indigo-600 to-teal-600 text-white text-sm font-semibold shadow-md shadow-violet-500/20 hover:shadow-lg hover:shadow-violet-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none transition-all"

          >

            {isLoading ? (

              <>

                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />

                {AI_NAME} is working…

              </>

            ) : (

              <>

                <IconSparkles className="w-4 h-4" />

                Build My Learning Path

              </>

            )}

          </button>

        </form>

      </div>

    </div>

  )

}


