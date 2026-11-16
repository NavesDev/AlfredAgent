import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { VoicePill } from '../features/assistant/components/VoicePill'
import { usePanelOutOfSight } from '../features/assistant/hooks/usePanelOutOfSight'
import { useVoice } from '../features/assistant/hooks/useVoice'
import { ResultCard } from '../features/results/components/ResultCard'
import { usePresentation } from '../features/results/hooks/usePresentation'
import { useResultActions } from '../features/results/hooks/useResultActions'
import { openViewer, overlayAnchor, setHitRect } from '../lib/desktop'
import { hitRect, overlayShows, stackClasses, type Anchor } from '../lib/overlay'

/** Time the pill or the card takes to fade out before it unmounts (matches animate-pill-out). */
const LEAVE_MS = 220
/** The card leaves on its own after this long without the mouse on it (D13). */
const CARD_MS = 30_000

/**
 * The desktop overlay window: transparent, always on top, never focused, anchored to the
 * position preset (Settings → Geral). With the panel out of sight it shows the voice pill while
 * Alfred is busy, and turns it into the result card when a result is presented. Clicks go
 * through everywhere except over the card (`set_hit_rect`). The expanded mode opens the
 * `viewer` window instead.
 */
export function OverlayPage() {
  const { state, level } = useVoice()
  const presentation = usePresentation()
  const { open } = useResultActions()
  const current = presentation.current
  const active = state !== 'idle'
  const outOfSight = usePanelOutOfSight(active || current?.mode === 'card')
  const shows = overlayShows({ active, outOfSight, presentation: current })
  const [anchor, setAnchor] = useState<Anchor>({ edge: 'top', align: 'right' })
  // What was on screen before, kept a moment so it fades out instead of vanishing.
  const [was, setWas] = useState(shows)
  const [leaving, setLeaving] = useState<'pill' | 'card' | null>(null)
  const [lastCard, setLastCard] = useState(current)
  const card = useRef<HTMLDivElement>(null)
  if (shows !== was) {
    setWas(shows)
    setLeaving(was === 'none' ? null : was)
  }
  if (shows === 'card' && current && current !== lastCard) setLastCard(current)

  useEffect(() => {
    document.documentElement.classList.add('overlay')
    void overlayAnchor()
      .then(setAnchor)
      .catch(() => {})
    return () => document.documentElement.classList.remove('overlay')
  }, [])

  useEffect(() => {
    if (current?.mode === 'ampliado') void openViewer(current.result.id, 0).catch(() => {})
  }, [current])

  useLayoutEffect(() => {
    const el = card.current
    if (shows !== 'card' || !el) {
      void setHitRect(null).catch(() => {})
      return
    }
    // The layout box, not getBoundingClientRect: that one includes the entrance animation's
    // scale and offset, and nothing reports again when the animation ends.
    const report = () =>
      void setHitRect(
        hitRect({
          left: el.offsetLeft,
          top: el.offsetTop,
          width: el.offsetWidth,
          height: el.offsetHeight,
        }),
      ).catch(() => {})
    report()
    const observer = new ResizeObserver(report)
    observer.observe(el)
    return () => observer.disconnect()
  }, [shows])

  useEffect(() => {
    if (!leaving) return
    const timer = setTimeout(() => setLeaving(null), LEAVE_MS)
    return () => clearTimeout(timer)
  }, [leaving])

  const cell = 'col-start-1 row-start-1'
  return (
    <div className={`grid h-full p-2 ${stackClasses(anchor)}`}>
      {shows === 'card' && current && (
        <div key={current.result.id} ref={card} className={`${cell} animate-pill-in`}>
          <ResultCard
            result={current.result}
            local
            onExpand={(slide) => void openViewer(current.result.id, slide).catch(() => {})}
            onOpen={(index, reveal) => open.mutate({ id: current.result.id, index, reveal })}
            onClose={presentation.close}
            autoCloseMs={CARD_MS}
            onDismiss={presentation.dismiss}
          />
        </div>
      )}
      {leaving === 'card' && shows !== 'card' && lastCard && (
        <div aria-hidden className={`${cell} pointer-events-none animate-pill-out`}>
          <ResultCard
            result={lastCard.result}
            local
            onExpand={() => {}}
            onOpen={() => {}}
            onClose={() => {}}
          />
        </div>
      )}
      {(shows === 'pill' || leaving === 'pill') && (
        <div className={cell}>
          <VoicePill state={state} level={level} leaving={shows !== 'pill'} />
        </div>
      )}
    </div>
  )
}
