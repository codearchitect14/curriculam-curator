import { scoreColor, scoreBg } from '../utils/format'

const FIT_METRICS = [
  { key: 'budget_adherence', label: 'Budget', short: 'Budget' },
  { key: 'marginal_coverage', label: 'Coverage', short: 'Cover.' },
  { key: 'known_topic_avoidance', label: 'Known Avoid', short: 'Known' },
  { key: 'constraint_adherence', label: 'Constraints', short: 'Constr.' },
  { key: 'audience_signal_score', label: 'Audience Signal', short: 'Audience' },
]

const AUDIT_METRICS = [
  { key: 'reason_quality', label: 'Inclusion Reasons', short: 'Include' },
  { key: 'drop_decision_quality', label: 'Drop Decisions', short: 'Drops' },
  { key: 'counterfactual_regret', label: 'Counterfactual', short: 'Swap' },
  { key: 'decision_redundancy', label: 'Redundancy', short: 'Dedup' },
]

const INTERPRETATIONS = {
  budget_adherence: 'How well total watch time fits the budget',
  marginal_coverage: 'Semantic coverage of unknown topics with unique contributions',
  known_topic_avoidance: 'Avoidance of already-known topic content',
  constraint_adherence: 'Respect for learner constraints and preferences',
  audience_signal_score: 'Persona-relevant signals from YouTube audience comments',
  reason_quality: 'Persona-tied, content-grounded inclusion reasons',
  drop_decision_quality: 'Whether excluded videos were correctly dropped',
  counterfactual_regret: 'Whether any dropped video should have replaced an included one',
  decision_redundancy: 'Penalty for redundant or zero-value inclusions',
}

function RadarChart({ scores, metrics }) {
  const cx = 160
  const cy = 160
  const maxR = 110
  const n = metrics.length
  const angleStep = (2 * Math.PI) / n

  function point(i, value) {
    const angle = -Math.PI / 2 + i * angleStep
    const r = (value ?? 0) * maxR
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
  }

  function polygonPoints(radius) {
    return Array.from({ length: n }, (_, i) => {
      const angle = -Math.PI / 2 + i * angleStep
      return `${cx + radius * Math.cos(angle)},${cy + radius * Math.sin(angle)}`
    }).join(' ')
  }

  const dataPoints = metrics.map((m, i) => point(i, scores[m.key] ?? 0))
  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')

  return (
    <svg viewBox="0 0 320 320" className="w-full max-w-xs mx-auto">
      {[0.25, 0.5, 0.75, 1.0].map((level) => (
        <polygon
          key={level}
          points={polygonPoints(maxR * level)}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="1"
        />
      ))}
      {metrics.map((_, i) => {
        const p = point(i, 1)
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e2e8f0" strokeWidth="1" />
      })}
      <polygon
        points={dataPolygon}
        fill="rgba(124, 58, 237, 0.15)"
        stroke="#7c3aed"
        strokeWidth="2"
      />
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="5" fill="#7c3aed" stroke="white" strokeWidth="2" />
      ))}
      {metrics.map((m, i) => {
        const labelPt = point(i, 1.22)
        return (
          <text
            key={m.key}
            x={labelPt.x}
            y={labelPt.y}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#64748b"
            style={{ fontSize: '10px', fontWeight: 500 }}
          >
            {m.short}
          </text>
        )
      })}
    </svg>
  )
}

function MetricBars({ evalResult, metrics }) {
  return (
    <div className="space-y-3">
      {metrics.map((m) => {
        const raw = evalResult[m.key]
        const score = raw ?? null
        const display = score === null ? 'n/a' : `${(score * 100).toFixed(0)}%`
        return (
          <div key={m.key}>
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-sm font-medium text-slate-700">{m.label}</span>
              <span
                className={`text-sm font-semibold tabular-nums ${
                  score === null ? 'text-slate-400' : scoreColor(score)
                }`}
              >
                {display}
              </span>
            </div>
            {score !== null && (
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${scoreBg(score)}`}
                  style={{ width: `${score * 100}%` }}
                />
              </div>
            )}
            <p className="text-xs text-slate-400 mt-1">{INTERPRETATIONS[m.key]}</p>
          </div>
        )
      })}
    </div>
  )
}

const SEVERITY_STYLES = {
  high: 'border-rose-200 bg-rose-50 text-rose-800',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  low: 'border-slate-200 bg-slate-50 text-slate-700',
}

export default function EvalDashboard({ evalResult }) {
  const { token_cost_estimate: tokens } = evalResult
  const overall = evalResult.overall_score
  const fitMetrics = FIT_METRICS.filter(
    (m) => m.key !== 'audience_signal_score' || evalResult.audience_signal_score != null
  )

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-card overflow-hidden animate-fade-in">
      <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
        <h3 className="text-sm font-semibold text-slate-900">Quality Evaluation</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Two-tier scoring: curriculum fit (60%) + decision audit (40%)
        </p>
      </div>

      <div className="p-5 space-y-6">
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="lg:w-2/5 flex flex-col items-center justify-center">
            <div className="text-center mb-2">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Overall</p>
              <p className={`text-5xl font-bold tabular-nums ${scoreColor(overall)}`}>
                {(overall * 100).toFixed(0)}
                <span className="text-2xl text-slate-400">%</span>
              </p>
            </div>
            <div className="flex gap-4 text-center text-xs mb-2">
              <div>
                <p className="text-slate-400">Fit</p>
                <p className={`font-semibold tabular-nums ${scoreColor(evalResult.curriculum_fit_score)}`}>
                  {(evalResult.curriculum_fit_score * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-slate-400">Audit</p>
                <p className={`font-semibold tabular-nums ${scoreColor(evalResult.decision_audit_score)}`}>
                  {(evalResult.decision_audit_score * 100).toFixed(0)}%
                </p>
              </div>
            </div>
            <RadarChart scores={evalResult} metrics={fitMetrics} />
          </div>

          <div className="lg:w-3/5 space-y-5">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                Curriculum Fit
              </h4>
              <MetricBars evalResult={evalResult} metrics={fitMetrics} />
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                Decision Audit
              </h4>
              <MetricBars evalResult={evalResult} metrics={AUDIT_METRICS} />
            </div>
          </div>
        </div>

        {evalResult.audience_signal_details?.length > 0 && (
          <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
              Audience Signal by Video
            </h4>
            <div className="space-y-2">
              {evalResult.audience_signal_details.map((detail) => (
                <div key={detail.video_id} className="text-xs text-slate-600">
                  <div className="flex justify-between gap-2">
                    <span className="font-medium text-slate-800 truncate">{detail.title}</span>
                    <span className={`font-semibold tabular-nums shrink-0 ${scoreColor(detail.score)}`}>
                      {detail.comments_disabled ? 'n/a' : `${(detail.score * 100).toFixed(0)}%`}
                    </span>
                  </div>
                  {detail.evidence && (
                    <p className="mt-1 text-slate-500 italic">"{detail.evidence}"</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {evalResult.decision_flags?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Decision Flags
            </h4>
            <div className="space-y-2">
              {evalResult.decision_flags.map((flag, idx) => (
                <div
                  key={`${flag.video_id}-${flag.flag_type}-${idx}`}
                  className={`rounded-lg border px-3 py-2 text-xs ${SEVERITY_STYLES[flag.severity] || SEVERITY_STYLES.medium}`}
                >
                  <p className="font-semibold">
                    {flag.flag_type.replace(/_/g, ' ')} — {flag.title}
                  </p>
                  <p className="mt-1 opacity-90">{flag.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {tokens && (
          <div className="flex flex-wrap gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-600">
            <div>
              <span className="text-slate-400">Input tokens</span>
              <p className="font-semibold text-slate-800 tabular-nums">
                {tokens.input_tokens?.toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-slate-400">Output tokens</span>
              <p className="font-semibold text-slate-800 tabular-nums">
                {tokens.output_tokens?.toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-slate-400">Est. cost</span>
              <p className="font-semibold text-slate-800">${tokens.estimated_usd?.toFixed(4)}</p>
            </div>
          </div>
        )}

        {evalResult.eval_notes && (
          <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-100 pt-3">
            {evalResult.eval_notes}
          </p>
        )}
      </div>
    </div>
  )
}
