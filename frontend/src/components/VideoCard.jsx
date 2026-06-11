import { formatDuration, formatViewCount } from '../utils/format'

import { IconExternalLink, IconPlay } from './Icons'



function confidenceBarColor(confidence) {

  if (confidence > 0.8) return 'bg-emerald-500'

  if (confidence >= 0.6) return 'bg-amber-500'

  return 'bg-rose-500'

}



export default function VideoCard({ entry }) {

  const { rank, video, inclusion_reason, confidence, covers_topics } = entry

  const pct = Math.round(confidence * 100)

  const thumb = `https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`



  return (

    <article className="group rounded-2xl border border-slate-200/80 bg-white shadow-card overflow-hidden hover:shadow-elevated hover:border-violet-200/60 transition-all duration-200 animate-fade-in">

      <div className="flex flex-col sm:flex-row">

        <a

          href={video.url}

          target="_blank"

          rel="noopener noreferrer"

          className="relative sm:w-52 shrink-0 aspect-video sm:aspect-auto sm:h-auto bg-slate-100 overflow-hidden"

        >

          <img

            src={thumb}

            alt=""

            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"

          />

          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">

            <span className="opacity-0 group-hover:opacity-100 transition-opacity w-10 h-10 rounded-full bg-white/90 flex items-center justify-center text-violet-600 shadow-lg">

              <IconPlay className="w-5 h-5 ml-0.5" />

            </span>

          </div>

          <span className="absolute bottom-2 right-2 px-1.5 py-0.5 text-xs font-medium rounded bg-black/75 text-white">

            {formatDuration(video.duration_minutes)}

          </span>

        </a>



        <div className="flex-1 p-4 sm:p-5 min-w-0">

          <div className="flex items-start gap-3">

            <span className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white text-xs font-bold shadow-sm">

              {rank}

            </span>

            <div className="flex-1 min-w-0">

              <a

                href={video.url}

                target="_blank"

                rel="noopener noreferrer"

                className="inline-flex items-start gap-1.5 text-base font-semibold text-slate-900 hover:text-violet-600 transition-colors leading-snug"

              >

                <span className="line-clamp-2">{video.title}</span>

                <IconExternalLink className="w-3.5 h-3.5 shrink-0 mt-1 opacity-0 group-hover:opacity-60" />

              </a>

              <p className="text-xs text-slate-500 mt-1">

                {video.channel} · {formatViewCount(video.view_count)}

              </p>

            </div>

          </div>



          <div className="mt-4">

            <div className="flex justify-between text-xs mb-1.5">

              <span className="font-medium text-slate-500">Confidence</span>

              <span className={`font-semibold tabular-nums ${confidence > 0.8 ? 'text-emerald-600' : confidence >= 0.6 ? 'text-amber-600' : 'text-rose-600'}`}>

                {confidence.toFixed(2)}

              </span>

            </div>

            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">

              <div

                className={`h-full rounded-full transition-all ${confidenceBarColor(confidence)}`}

                style={{ width: `${pct}%` }}

              />

            </div>

          </div>



          <div className="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-100">

            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">Why included</p>

            <p className="text-sm text-slate-700 leading-relaxed">{inclusion_reason}</p>

          </div>



          {covers_topics.length > 0 && (

            <div className="mt-3 flex flex-wrap gap-1.5">

              {covers_topics.map((topic) => (

                <span

                  key={topic}

                  className="px-2.5 py-1 text-xs font-medium rounded-lg bg-violet-50 text-violet-700 border border-violet-100"

                >

                  {topic}

                </span>

              ))}

            </div>

          )}

        </div>

      </div>

    </article>

  )

}


