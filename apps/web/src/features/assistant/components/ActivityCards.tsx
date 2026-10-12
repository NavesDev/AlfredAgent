import { useEffect, useState } from 'react'
import type { Activity } from '../hooks/useActivity'
import { SHOWN } from '../lib/activity'
import { ActivityScene } from './scenes/ActivityScene'

const GAP = 196 // card width plus the space between cards, in px
const FADE_MS = 350

/** The cards to draw: the live ones, or the last ones while they fade out after the reply. */
function useLeaving(items: Activity[]) {
  const [last, setLast] = useState(items)
  if (items.length && items !== last) setLast(items)
  const leaving = !items.length && last.length > 0
  useEffect(() => {
    if (!leaving) return
    const timer = setTimeout(() => setLast([]), FADE_MS)
    return () => clearTimeout(timer)
  }, [leaving])
  return { shown: items.length ? items : last, leaving }
}

/** Where each card sits: the newest at the right of a centered row, the extra one leaving left. */
function place(index: number, count: number) {
  const shown = Math.min(count, SHOWN)
  const slot = index - (count - shown)
  if (slot < 0) return { x: -((shown + 1) / 2) * GAP - 60, scale: 0.85, opacity: 0 }
  const current = slot === shown - 1
  return {
    x: (slot - (shown - 1) / 2) * GAP,
    scale: current ? 1 : 0.94,
    opacity: current ? 1 : 0.55,
  }
}

/**
 * What Alfred is doing, as a row of up to three cards with a pixel scene each: a new step comes
 * in at the right and pushes the others left; the oldest slides out. It sits in the space the
 * orb leaves when it rises, and fades out with the reply.
 */
export function ActivityCards({ items: live }: { items: Activity[] }) {
  const { shown: items, leaving } = useLeaving(live)
  const latest = items.at(-1)
  return (
    <div
      style={{ transitionDuration: `${FADE_MS}ms` }}
      className={`pointer-events-none absolute inset-x-0 bottom-0 h-36 transition-opacity ${
        leaving ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <p className="sr-only" aria-live="polite">
        {!leaving && latest && `${latest.label}${latest.detail ? `: ${latest.detail}` : ''}`}
      </p>
      {items.map((item, i) => {
        const current = item === latest
        const { x, scale, opacity } = place(i, items.length)
        return (
          <div
            key={item.id}
            aria-hidden="true"
            style={{ transform: `translateX(${x}px) scale(${scale})`, opacity }}
            className="absolute top-1 left-1/2 -ml-[92px] w-[184px] transition-[transform,opacity] duration-600 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
          >
            <div
              className={`animate-card-in rounded-xl border bg-[#0c1120]/90 p-1.5 text-[11px] backdrop-blur ${
                current ? 'border-amber-300/40' : 'border-white/10'
              }`}
            >
              <div className="rounded-lg bg-[#0a0e1a] px-2 py-1">
                <ActivityScene action={item.action} still={!current} className="h-[72px] w-full" />
              </div>
              <p
                className={`mt-1.5 flex items-center gap-1 truncate px-0.5 ${
                  current ? 'text-amber-200' : 'text-gray-400'
                }`}
              >
                <span className="truncate">
                  {item.label}
                  {current && '…'}
                </span>
                {!current && <span className="ml-auto text-gray-500">✓</span>}
              </p>
              <p className="min-h-4 truncate px-0.5 font-mono text-gray-500">{item.detail}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
