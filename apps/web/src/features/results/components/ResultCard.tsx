import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { ResultView } from '../../../api/events'
import { ChevronLeft, ChevronRight, Monitor, X } from '../../../components/icons'
import { formatSize, mainAction, slidesOf } from '../lib/results'
import { MiniOrb } from './MiniOrb'
import { ResultBody } from './ResultBody'

type Props = {
  result: ResultView
  /** This computer: media and files show; elsewhere only text (RN-12). */
  local: boolean
  onExpand: (slide: number) => void
  /** Opens the file in its app, or (`reveal`) its folder. */
  onOpen: (index: number, reveal: boolean) => void
  /** ✕: closes it everywhere. */
  onClose: () => void
  /** Leaves on its own after this long without the mouse on it. */
  autoCloseMs?: number
  onDismiss?: () => void
}

const button =
  'h-6 shrink-0 rounded-full bg-fill px-2.5 text-[11px] font-medium text-ink transition hover:bg-fill-on'
const primary =
  'h-6 shrink-0 rounded-full bg-ink px-2.5 text-[11px] font-medium text-[#111] transition hover:bg-white'
const round =
  'grid size-[22px] shrink-0 place-items-center rounded-full bg-fill text-ink transition hover:bg-fill-on'

/** The result card (Dynamic Island style): 300px of the pill's dark glass. */
export function ResultCard({
  result,
  local,
  onExpand,
  onOpen,
  onClose,
  autoCloseMs,
  onDismiss,
}: Props) {
  const slides = slidesOf(result)
  const [at, setAt] = useState(0)
  const [hover, setHover] = useState(false)
  const slide = slides[Math.min(at, slides.length - 1)]

  // Kept in a ref: the parents re-render many times a second (voice level), and a new
  // onDismiss each time would restart the timer forever.
  const dismiss = useRef(onDismiss)
  useEffect(() => {
    dismiss.current = onDismiss
  })
  useEffect(() => {
    if (!autoCloseMs || hover) return
    const timer = setTimeout(() => dismiss.current?.(), autoCloseMs)
    return () => clearTimeout(timer)
  }, [autoCloseMs, hover, result.id])

  // The overlay turns click-through when the mouse leaves the card, which can swallow
  // mouseleave; leaving the window or the page losing focus also ends the hover.
  useEffect(() => {
    if (!hover) return
    const end = () => setHover(false)
    document.documentElement.addEventListener('mouseleave', end)
    window.addEventListener('blur', end)
    return () => {
      document.documentElement.removeEventListener('mouseleave', end)
      window.removeEventListener('blur', end)
    }
  }, [hover])

  return (
    <section
      aria-label={result.title}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="flex w-[300px] flex-col gap-2 surface rounded-[22px] p-2.5 text-ink select-none"
    >
      <header className="flex min-w-0 items-center gap-2 text-xs">
        <MiniOrb />
        <b className="min-w-0 flex-1 truncate font-semibold">{result.title}</b>
        {local && slides.length > 1 && (
          <span className="flex items-center gap-0.5 text-ink-2 tabular-nums">
            <button
              type="button"
              aria-label="Anterior"
              disabled={at === 0}
              onClick={() => setAt(at - 1)}
              className="disabled:opacity-30"
            >
              <ChevronLeft className="size-3.5" />
            </button>
            {at + 1} de {slides.length}
            <button
              type="button"
              aria-label="Próximo"
              disabled={at === slides.length - 1}
              onClick={() => setAt(at + 1)}
              className="disabled:opacity-30"
            >
              <ChevronRight className="size-3.5" />
            </button>
          </span>
        )}
        <button type="button" aria-label="Fechar" onClick={onClose} className={round}>
          <X className="size-3" />
        </button>
      </header>

      {!local ? (
        <Elsewhere result={result} />
      ) : (
        <>
          <div className="aspect-video overflow-hidden rounded-[14px] bg-[#0e0e11] ring-1 ring-white/6">
            {slide && <ResultBody result={result} slide={slide} size="card" />}
          </div>
          <Footer>
            {slide?.type === 'file' ? (
              <>
                <span className="min-w-0 flex-1 truncate text-ink-2">
                  {slide.file.name}
                  {slide.file.exists && slide.file.kind === 'other'
                    ? ` · ${formatSize(slide.file.size)}`
                    : ''}
                </span>
                {mainAction(slide.file) !== 'none' && (
                  <button
                    type="button"
                    className={button}
                    onClick={() => onOpen(slide.index, true)}
                  >
                    Pasta
                  </button>
                )}
                {mainAction(slide.file) === 'expand' && (
                  <button type="button" className={primary} onClick={() => onExpand(at)}>
                    Ampliar
                  </button>
                )}
                {mainAction(slide.file) === 'open' && (
                  <button
                    type="button"
                    className={primary}
                    onClick={() => onOpen(slide.index, false)}
                  >
                    Abrir no app
                  </button>
                )}
              </>
            ) : (
              <>
                <span className="flex-1" />
                <button type="button" className={primary} onClick={() => onExpand(at)}>
                  Ampliar
                </button>
              </>
            )}
          </Footer>
        </>
      )}
    </section>
  )
}

function Footer({ children }: { children: ReactNode }) {
  return <div className="flex min-w-0 items-center gap-1.5 text-[11px]">{children}</div>
}

/** Another device on the local network: words only, never media or files. */
function Elsewhere({ result }: { result: ResultView }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-[14px] bg-[#0e0e11] px-3 py-2.5 text-[11.5px]">
      {result.summary && <span>{result.summary}</span>}
      {result.report && <p className="m-0 line-clamp-4 text-ink-2">{result.report}</p>}
      {result.changes.slice(0, 3).map((c) => (
        <span key={c.path} className="flex gap-1.5 tabular-nums">
          <span className="min-w-0 flex-1 truncate text-ink-2">{c.path}</span>
          <span className="text-apple-green">+{c.added}</span>
          <span className="text-[#ff6961]">−{c.removed}</span>
        </span>
      ))}
      <span className="flex items-center gap-1.5 text-ink-2">
        <Monitor className="size-3.5" />
        Arquivos só no computador
      </span>
    </div>
  )
}
