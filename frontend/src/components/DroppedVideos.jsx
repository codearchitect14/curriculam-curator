import { useState } from 'react'

import { formatDuration } from '../utils/format'

import { IconChevronDown } from './Icons'



export default function DroppedVideos({ dropped }) {

  const [open, setOpen] = useState(false)



  if (!dropped || dropped.length === 0) return null



  return (

    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-card overflow-hidden">

      <button

        type="button"

        onClick={() => setOpen(!open)}

        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors text-left"

      >

        <div>

          <h3 className="text-sm font-semibold text-slate-800">

            Excluded videos

          </h3>

          <p className="text-xs text-slate-500 mt-0.5">

            {dropped.length} video{dropped.length !== 1 ? 's' : ''} not included in curriculum

          </p>

        </div>

        <div className="flex items-center gap-2">

          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600">

            {dropped.length}

          </span>

          <IconChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />

        </div>

      </button>



      {open && (

        <div className="border-t border-slate-100 divide-y divide-slate-100 max-h-80 overflow-y-auto">

          {dropped.map((d) => (

            <div key={d.video.video_id} className="px-5 py-3 hover:bg-slate-50/50">

              <div className="flex items-start justify-between gap-3">

                <div className="min-w-0">

                  <p className="text-sm font-medium text-slate-800 truncate">{d.video.title}</p>

                  <p className="text-xs text-slate-500 mt-0.5">

                    {d.video.channel} · {formatDuration(d.video.duration_minutes)}

                  </p>

                </div>

              </div>

              <div className="flex items-center gap-2 mt-2">
                {d.drop_stage && (
                  <span
                    className={`shrink-0 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide rounded-full ${
                      d.drop_stage === 'budget'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {d.drop_stage}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed bg-rose-50/50 border border-rose-100/50 rounded-lg px-3 py-2">
                {d.drop_reason}
              </p>

            </div>

          ))}

        </div>

      )}

    </div>

  )

}


