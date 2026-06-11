import { useState } from 'react'

import VideoCard from './VideoCard'

import DroppedVideos from './DroppedVideos'

import FollowUpChat from './FollowUpChat'

import EvalDashboard from './EvalDashboard'

import { evaluateCurriculum } from '../api/client'

import { formatDuration } from '../utils/format'

import { AI_NAME } from '../constants/brand'
import AiCompanion from './AiCompanion'
import { IconChart, IconChat, IconChevronDown, IconClock, IconSparkles, IconVideo } from './Icons'



const TABS = [

  { id: 'curriculum', label: 'Curriculum', icon: IconVideo },

  { id: 'chat', label: `Ask ${AI_NAME}`, icon: IconChat },

  { id: 'eval', label: 'Evaluation', icon: IconChart },

]



function StatCard({ icon: Icon, label, value, sub }) {

  return (

    <div className="rounded-xl border border-slate-200/80 bg-white px-4 py-3 shadow-card">

      <div className="flex items-center gap-2 text-slate-400 mb-1">

        <Icon className="w-4 h-4" />

        <span className="text-xs font-medium">{label}</span>

      </div>

      <p className="text-lg font-semibold text-slate-900 tabular-nums">{value}</p>

      {sub && <p className="text-xs text-slate-500">{sub}</p>}

    </div>

  )

}



export default function CurriculumView({

  curriculum,

  activePersona,

  evalResult,

  setEvalResult,

}) {

  const [activeTab, setActiveTab] = useState('curriculum')

  const [notesOpen, setNotesOpen] = useState(false)

  const [evalLoading, setEvalLoading] = useState(false)

  const [evalError, setEvalError] = useState(null)



  const overBudget = curriculum.total_minutes > curriculum.budget_minutes

  const budgetPct = Math.min(100, (curriculum.total_minutes / curriculum.budget_minutes) * 100)



  async function handleRunEval() {

    if (!activePersona) return

    setEvalLoading(true)

    setEvalError(null)

    setActiveTab('eval')

    try {

      const result = await evaluateCurriculum(activePersona, curriculum)

      setEvalResult(result)

    } catch (err) {

      setEvalError(err.message)

    } finally {

      setEvalLoading(false)

    }

  }



  return (

    <div className="space-y-5 animate-fade-in">

      <AiCompanion
        size="md"
        message={`I put together ${curriculum.entries.length} videos for your journey.`}
        submessage="Each one was chosen for your goals, time budget, and learning style. Browse below or ask me why."
      />

      <div className="rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur-sm shadow-card overflow-hidden">

        <div className="px-5 py-5 sm:px-6 bg-gradient-to-r from-violet-600/5 via-indigo-600/5 to-transparent border-b border-slate-100">

          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">

            <div className="min-w-0">

              <span className="inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full bg-violet-100 text-violet-700 mb-2">

                {curriculum.persona_id.replace(/_/g, ' ')}

              </span>

              <h2 className="text-lg sm:text-xl font-semibold text-slate-900 leading-snug">

                {curriculum.goal}

              </h2>

            </div>

            <button

              type="button"

              onClick={handleRunEval}

              disabled={evalLoading}

              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50 transition-colors shrink-0 shadow-sm"

            >

              {evalLoading ? (

                <>

                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />

                  Evaluating…

                </>

              ) : (

                <>

                  <IconChart className="w-4 h-4" />

                  Run Evaluation

                </>

              )}

            </button>

          </div>



          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">

            <StatCard icon={IconVideo} label="Videos" value={curriculum.entries.length} />

            <StatCard icon={IconClock} label="Watch time" value={formatDuration(curriculum.total_minutes)} sub={`of ${formatDuration(curriculum.budget_minutes)} budget`} />

            <StatCard icon={IconSparkles} label="Dropped" value={curriculum.dropped.length} sub="excluded candidates" />

            <StatCard

              icon={IconChart}

              label="Overall score"

              value={evalResult ? `${(evalResult.overall_score * 100).toFixed(0)}%` : '—'}

              sub={evalResult ? 'evaluated' : 'not run yet'}

            />

          </div>



          <div className="mt-5">

            <div className="flex justify-between text-xs font-medium mb-1.5">

              <span className="text-slate-500">Budget utilization</span>

              <span className={overBudget ? 'text-rose-600' : 'text-slate-700'}>

                {curriculum.total_minutes.toFixed(0)} / {curriculum.budget_minutes} min

              </span>

            </div>

            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">

              <div

                className={`h-full rounded-full transition-all ${overBudget ? 'bg-rose-500' : 'bg-gradient-to-r from-violet-500 to-indigo-500'}`}

                style={{ width: `${budgetPct}%` }}

              />

            </div>

          </div>

        </div>



        {/* Tabs */}

        <div className="flex border-b border-slate-100 px-2">

          {TABS.map((tab) => {

            const Icon = tab.icon

            const isActive = activeTab === tab.id

            return (

              <button

                key={tab.id}

                type="button"

                onClick={() => setActiveTab(tab.id)}

                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px ${

                  isActive

                    ? 'border-violet-600 text-violet-700'

                    : 'border-transparent text-slate-500 hover:text-slate-700'

                }`}

              >

                <Icon className="w-4 h-4" />

                {tab.label}

                {tab.id === 'eval' && evalResult && (

                  <span className="w-2 h-2 rounded-full bg-emerald-500" />

                )}

              </button>

            )

          })}

        </div>

      </div>



      {evalError && (

        <div className="text-sm text-rose-700 bg-rose-50 border border-rose-100 px-4 py-3 rounded-xl">

          {evalError}

        </div>

      )}



      {activeTab === 'curriculum' && (

        <div className="space-y-4">

          {curriculum.entries.map((entry) => (

            <VideoCard key={entry.video.video_id} entry={entry} />

          ))}



          {curriculum.agent_notes && (

            <div className="rounded-2xl border border-slate-200/80 bg-white shadow-card overflow-hidden">

              <button

                type="button"

                onClick={() => setNotesOpen(!notesOpen)}

                className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors text-left"

              >

                <div>

                  <h3 className="text-sm font-semibold text-slate-800">How I built this path</h3>

                  <p className="text-xs text-slate-500 mt-0.5">{AI_NAME}&apos;s strategy for your persona</p>

                </div>

                <IconChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${notesOpen ? 'rotate-180' : ''}`} />

              </button>

              {notesOpen && (

                <div className="px-5 pb-5 text-sm text-slate-700 leading-relaxed border-t border-slate-100 pt-4 bg-slate-50/30">

                  {curriculum.agent_notes}

                </div>

              )}

            </div>

          )}



          <DroppedVideos dropped={curriculum.dropped} />

        </div>

      )}



      {activeTab === 'chat' && (

        <FollowUpChat curriculum={curriculum} persona={activePersona} />

      )}



      {activeTab === 'eval' && (

        <>

          {evalLoading && !evalResult && (

            <div className="rounded-2xl border border-slate-200/80 bg-white p-12 text-center shadow-card">

              <span className="inline-block w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin mb-3" />

              <p className="text-sm text-slate-600">Running evaluation metrics…</p>

            </div>

          )}

          {!evalLoading && !evalResult && (

            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-12 text-center">

              <IconChart className="w-10 h-10 text-slate-300 mx-auto mb-3" />

              <p className="text-sm text-slate-600 mb-4">No evaluation yet</p>

              <button

                type="button"

                onClick={handleRunEval}

                className="px-4 py-2 rounded-xl bg-violet-600 text-white text-sm font-medium hover:bg-violet-700"

              >

                Run Evaluation

              </button>

            </div>

          )}

          {evalResult && <EvalDashboard evalResult={evalResult} />}

        </>

      )}

    </div>

  )

}


