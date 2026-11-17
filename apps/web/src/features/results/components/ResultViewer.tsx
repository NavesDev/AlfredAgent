import { useEffect, type ReactNode } from 'react'
import type { ResultView } from '../../../api/events'
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Folder,
  X,
} from '../../../components/icons'
import { Room } from '../../../components/layout/AppShell'
import { fileUrl, formatSize, slidesOf, timeLabel, type Slide } from '../lib/results'
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

/** Glass pill and round buttons, as on the panel's title bar and control bar. */
const pill =
  'glass flex h-8 shrink-0 items-center gap-1.5 rounded-full px-3.5 text-[12.5px] font-medium text-ink transition hover:bg-fill-on'
const round =
  'grid size-8 shrink-0 place-items-center rounded-full text-ink transition hover:bg-fill-on disabled:pointer-events-none disabled:opacity-30'

const KIND: Record<string, string> = {
  image: 'Imagem',
  video: 'Vídeo',
  pdf: 'PDF',
  markdown: 'Markdown',
  text: 'Texto',
  html: 'Página',
}

/** What the subtitle says about a slide: its kind and size, or "Relatório". */
function detail(slide: Slide | undefined) {
  if (!slide || slide.type === 'report') return 'Relatório'
  const kind = KIND[slide.file.kind] ?? 'Arquivo'
  return slide.file.exists ? `${kind} · ${formatSize(slide.file.size)}` : kind
}

/** How the slide sits in the window: text in a reading column, PDF and pages a little wider,
 * all on a dark panel; images, video and file cards keep their own size with no panel. */
function frame(slide: Slide | undefined) {
  const panel =
    'h-full overflow-hidden rounded-card border border-white/10 bg-[#141417] shadow-[inset_0_1px_0_rgb(255_255_255/0.06),0_24px_60px_rgb(0_0_0/0.45)]'
  if (!slide || slide.type === 'report') return `${panel} max-w-[860px]`
  if (!slide.file.exists) return 'h-full'
  switch (slide.file.kind) {
    case 'markdown':
    case 'text':
      return `${panel} max-w-[860px]`
    case 'pdf':
      return `${panel} max-w-[860px]`
    case 'html':
      return `${panel} max-w-[1200px]`
    case 'image':
    case 'video':
      return 'h-full'
    default:
      return 'h-full'
  }
}

/** The expanded view (Quick Look style) in the panel's look: the graphite room, a title bar
 * with glass buttons, the slide on a glass panel and an ornament pill to move between files. */
export function ResultViewer({ result, index, local, onIndex, onOpen, onClose }: Props) {
  const slides = slidesOf(result)
  const at = Math.max(0, Math.min(index, slides.length - 1))
  const slide = slides[at]
  const many = slides.length > 1

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
      className="relative flex size-full flex-col overflow-hidden rounded-[22px] border border-white/10 text-ink select-none"
    >
      <Room />

      {/* "deep": the whole bar drags the window, except its buttons (Tauri's drag.js). */}
      <header
        data-tauri-drag-region="deep"
        className="relative flex h-14 shrink-0 items-center gap-3 px-4"
      >
        <MiniOrb className="size-6" />
        <div className="flex min-w-0 flex-1 flex-col leading-tight">
          <b className="truncate text-[14px] font-semibold tracking-[-0.01em]">{name}</b>
          <span className="truncate text-[12px] text-ink-2">
            {result.session} · {timeLabel(result.created_at)} · {detail(slide)}
          </span>
        </div>
        {file && (
          <>
            <button type="button" className={pill} onClick={() => onOpen(file.index, false)}>
              <ExternalLink className="size-3.5" />
              Abrir no app
            </button>
            <button type="button" className={pill} onClick={() => onOpen(file.index, true)}>
              <Folder className="size-3.5" />
              Pasta
            </button>
          </>
        )}
        <button
          type="button"
          aria-label="Fechar"
          title="Fechar"
          onClick={onClose}
          className="glass grid size-8 shrink-0 place-items-center rounded-full text-ink transition hover:bg-apple-red/80"
        >
          <X className="size-3.5" />
        </button>
      </header>

      <div className={`relative min-h-0 flex-1 px-4 ${many ? 'pb-[84px]' : 'pb-4'}`}>
        <div className={`relative mx-auto w-full ${frame(slide)}`}>
          {slide && <ResultBody result={result} slide={slide} size="full" />}
        </div>
      </div>

      {many && (
        <nav
          aria-label="Arquivos"
          data-tauri-drag-region="deep"
          className="glass absolute bottom-4 left-1/2 flex max-w-[calc(100%-32px)] -translate-x-1/2 items-center gap-1.5 rounded-full p-1.5"
        >
          <button
            type="button"
            aria-label="Anterior"
            disabled={at === 0}
            onClick={() => onIndex(at - 1)}
            className={round}
          >
            <ChevronLeft className="size-4" />
          </button>
          <div className="no-scrollbar flex min-w-0 items-center gap-1 overflow-x-auto">
            {slides.map((s, i) => {
              const label = s.type === 'file' ? s.file.name : 'Relatório'
              const thumb =
                s.type === 'file' && s.file.exists && local && s.file.kind === 'image'
                  ? fileUrl(result.id, s.index)
                  : null
              return (
                <Chip key={label + i} label={label} current={i === at} onClick={() => onIndex(i)}>
                  {thumb ? (
                    <img src={thumb} alt="" className="size-6 rounded-full object-cover" />
                  ) : (
                    <FileText className="size-3.5 text-ink-2" />
                  )}
                </Chip>
              )
            })}
          </div>
          <span className="px-1.5 text-[12px] whitespace-nowrap text-ink-2 tabular-nums">
            {at + 1} de {slides.length}
          </span>
          <button
            type="button"
            aria-label="Próximo"
            disabled={at === slides.length - 1}
            onClick={() => onIndex(at + 1)}
            className={round}
          >
            <ChevronRight className="size-4" />
          </button>
        </nav>
      )}
    </section>
  )
}

/** One file in the ornament: icon (or a round thumbnail) and its full name. */
function Chip({
  label,
  current,
  onClick,
  children,
}: {
  label: string
  current: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-current={current}
      onClick={onClick}
      className="flex h-9 max-w-[280px] shrink-0 items-center gap-2 rounded-full px-3 text-[12.5px] font-medium text-ink-2 transition hover:text-ink aria-current:bg-fill-on aria-current:text-ink"
    >
      {children}
      <span className="truncate">{label}</span>
    </button>
  )
}
