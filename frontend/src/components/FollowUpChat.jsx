import { useState, useRef, useEffect } from 'react'
import { askFollowup } from '../api/client'
import { AI_NAME } from '../constants/brand'
import Logo from './Logo'
import { IconSend, IconUser } from './Icons'

const SUGGESTIONS = [
  'Why did you pick these videos for me?',
  'Which topics am I learning best from this path?',
  'Why did you leave some videos out?',
  'Am I staying within my time budget?',
]

function CuratorAvatar({ small = false }) {
  return <Logo size={small ? 'sm' : 'sm'} glow />
}

export default function FollowUpChat({ curriculum, persona }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendQuestion(question) {
    if (!question.trim() || loading || !persona) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setLoading(true)
    setError(null)

    try {
      const answer = await askFollowup(persona, curriculum, question)
      setMessages((prev) => [...prev, { role: 'assistant', text: answer }])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    sendQuestion(input.trim())
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur-sm shadow-card overflow-hidden flex flex-col h-[500px]">
      <div className="px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-violet-50/50 to-teal-50/30 shrink-0">
        <div className="flex items-center gap-3">
          <CuratorAvatar />
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Ask {AI_NAME}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              I remember every choice I made — ask me anything about your path
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="py-4">
            <div className="flex gap-3 mb-5">
              <CuratorAvatar />
              <div className="rounded-2xl rounded-tl-md bg-gradient-to-br from-violet-50 to-teal-50/50 border border-violet-100/50 px-4 py-3 text-sm text-slate-700 leading-relaxed max-w-md">
                I&apos;m happy to explain why I included or skipped any video.
                Try one of these — or ask your own question.
              </div>
            </div>
            <div className="flex flex-wrap gap-2 pl-11">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => sendQuestion(s)}
                  disabled={loading}
                  className="px-3 py-2 text-xs font-medium rounded-xl border border-violet-200/80 text-violet-700 bg-white hover:bg-violet-50 hover:border-violet-300 transition-colors disabled:opacity-50 text-left"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className="shrink-0 pt-0.5">
              {msg.role === 'user' ? (
                <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center">
                  <IconUser className="w-4 h-4" />
                </div>
              ) : (
                <CuratorAvatar />
              )}
            </div>
            <div
              className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-slate-800 text-white rounded-tr-md'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-tl-md shadow-sm'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <CuratorAvatar />
            <div className="px-4 py-3 rounded-2xl rounded-tl-md bg-white border border-slate-200 shadow-sm">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse-soft" />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse-soft" style={{ animationDelay: '0.2s' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse-soft" style={{ animationDelay: '0.4s' }} />
                </span>
                {AI_NAME} is thinking…
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-5 mb-2 text-xs text-rose-700 bg-rose-50 border border-rose-100 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-100 bg-slate-50/50 shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask ${AI_NAME} anything about your videos…`}
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 disabled:opacity-50"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-violet-600 to-teal-600 text-white hover:shadow-md disabled:opacity-50 transition-all shrink-0"
          >
            <IconSend className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
