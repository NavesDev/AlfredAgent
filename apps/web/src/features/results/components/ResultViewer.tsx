import { useEffect } from 'react'
import type { ResultView } from '../../../api/events'
import { ChevronLeft, ChevronRight, FileText, X } from '../../../components/icons'
import { fileUrl, slidesOf, timeLabel } from '../lib/results'
import { MiniOrb } from './MiniOrb'
import { ResultBody } from './ResultBody'

type Props = {
  result: ResultView
  /** Which slide (report first, then files). */
  index: number
  local: boolean
  onIndex: (index: number) => void
  onOpen: (file: number, reveal: boolean) => void
  onClose: () => void
}

const button =
  'h-7 shrink-0 rounded-full bg-fill px-3 text-xs font-medium text-ink transition hover:bg-fill-on'
const arrow =
  'glass absolute top-1/2 z-10 grid size-10 -translate-y-1/2 place-items-center rounded-full text-ink disabled:opacity-0'

/** The expanded view (Quick Look style): one big slide, arrows, a thumbnail strip, Esc closes. */
export function ResultViewer({ result, index, local, onIndex, onOpen, onClose }: Props) {
  const slides = slidesOf(result)
  const at = Math.max(0, Math.min(index, slides.length - 1))
  const slide = slides[at]

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft' && at > 0) onIndex(at - 1)
      if (e.key === 'ArrowRight' && at < slides.length - 1) onIndex(at + 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [at, slides.length, onIndex, onClose])

  const name = slide?.type === 'file' ? slide.file.name : result.title
  const file = slide?.type === 'file' && slide.file.exists && local ? slide : null

  return (
    <section
      aria-label={name}
      className="glass flex size-full flex-col overflow-hidden rounded-[18px] text-ink"
    >
      <header data-tauri-drag-region className="flex items-center gap-2 px-3.5 py-2.5 text-[13px]">
        <MiniOrb />
        <b className="min-w-0 flex-1 truncate font-semibold">{name}</b>
        <span className="hidden text-ink-2 sm:inline">
          {result.session} · {timeLabel(result.created_at)}
        </span>
        {file && (
          <>
            <button type="button" className={button} onClick={() => onOpen(file.index, false)}>
              Abrir no app
            </button>
            <button type="button" className={button} onClick={() => onOpen(file.index, true)}>
              Pasta
            </button>
          </>
        )}
        <button
          type="button"
          aria-label="Fechar"
          onClick={onClose}
          className="grid size-7 place-items-center rounded-full bg-fill hover:bg-fill-on"
        >
          <X className="size-3.5" />
        </button>
      </header>

      <div className="relative min-h-0 flex-1 bg-black/30">
        {slide && <ResultBody result={result} slide={slide} size="full" />}
        {slides.length > 1 && (
          <>
            <button
              type="button"
              aria-label="Anterior"
              disabled={at === 0}
              onClick={() => onIndex(at - 1)}
              className={`${arrow} left-3`}
            >
              <ChevronLeft />
            </button>
            <button
              type="button"
              aria-label="Próximo"
              disabled={at === slides.length - 1}
              onClick={() => onIndex(at + 1)}
              className={`${arrow} right-3`}
            >
              <ChevronRight />
            </button>
          </>
        )}
      </div>

      {slides.length > 1 && (
        <nav aria-label="Arquivos" className="flex justify-center gap-1.5 px-3 py-2">
          {slides.map((s, i) => {
            const label = s.type === 'file' ? s.file.name : 'Relatório'
            const thumb =
              s.type === 'file' && s.file.exists && local && s.file.kind === 'image'
                ? fileUrl(result.id, s.index)
                : null
            return (
              <button
                key={label + i}
                type="button"
                aria-label={label}
                aria-current={i === at}
                onClick={() => onIndex(i)}
                className="grid h-9 w-14 place-items-center overflow-hidden rounded-md bg-fill-on aria-current:outline-2 aria-current:outline-white"
              >
                {thumb ? (
                  <img src={thumb} alt="" className="size-full object-cover" />
                ) : (
                  <FileText className="size-4 text-ink-2" />
                )}
              </button>
            )
          })}
        </nav>
      )}
    </section>
  )
}
