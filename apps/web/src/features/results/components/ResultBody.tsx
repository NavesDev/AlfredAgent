import { useEffect, useRef, useState, type ReactNode } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResultView } from '../../../api/events'
import { FileX } from '../../../components/icons'
import { useFileText } from '../hooks/useFileText'
import { usePdf } from '../hooks/usePdf'
import {
  cleanMarkdown,
  fileUrl,
  formatSize,
  shownChanges,
  totals,
  type Slide,
} from '../lib/results'

export type Size = 'card' | 'full'

type Props = { result: ResultView; slide: Slide; size: Size }

/** The body of one slide, by kind: media, document, report or a file card. */
export function ResultBody({ result, slide, size }: Props) {
  if (slide.type === 'report') return <Report result={result} size={size} />
  const { file, index } = slide
  if (!file.exists)
    return size === 'card' ? (
      <Gone />
    ) : (
      <Small>
        <Gone />
      </Small>
    )
  const url = fileUrl(result.id, index)
  const fit = size === 'card' ? 'object-cover' : 'object-contain'
  switch (file.kind) {
    case 'image':
      return size === 'card' ? (
        <img src={url} alt={file.name} className={`size-full ${fit}`} />
      ) : (
        <Fitted>
          <img src={url} alt={file.name} className={`${FITTED} ${fit}`} />
        </Fitted>
      )
    case 'video': {
      const video = (
        <video
          src={url}
          aria-label={file.name}
          className={size === 'card' ? `size-full ${fit}` : `${FITTED} ${fit}`}
          autoPlay
          loop
          playsInline
          muted={size === 'card'}
          controls={size === 'full'}
        />
      )
      return size === 'card' ? video : <Fitted>{video}</Fitted>
    }
    case 'pdf':
      return <Pdf url={url} size={size} />
    case 'markdown':
      return <MarkdownFile id={result.id} index={index} size={size} />
    case 'text':
      return <TextFile id={result.id} index={index} />
    case 'html':
      return (
        <div className="relative size-full bg-white">
          <iframe
            title={file.name}
            src={url}
            sandbox="allow-scripts"
            referrerPolicy="no-referrer"
            className="size-full border-0"
          />
          <span className="absolute right-2 bottom-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] text-white">
            Isolado
          </span>
        </div>
      )
    default:
      return size === 'card' ? (
        <FileCard name={file.name} size={file.size} />
      ) : (
        <Small>
          <FileCard name={file.name} size={file.size} />
        </Small>
      )
  }
}

/** Media in the expanded view keeps its own size and shape, centered, never stretched. */
const FITTED =
  'max-h-full max-w-full rounded-[18px] border border-white/10 shadow-[0_24px_60px_rgb(0_0_0/0.5)]'

function Fitted({ children }: { children: ReactNode }) {
  return <div className="flex size-full items-center justify-center p-4 md:px-16 md:py-8">{children}</div>
}

/** A small dark card, centered: what has no preview in the expanded view. */
function Small({ children }: { children: ReactNode }) {
  return (
    <Fitted>
      <div className="h-28 w-full max-w-[380px] rounded-card border border-white/10 bg-[#141417] shadow-[0_24px_60px_rgb(0_0_0/0.45)]">
        {children}
      </div>
    </Fitted>
  )
}

export function Loading() {
  return (
    <div
      role="status"
      aria-label="Carregando"
      className="size-full animate-pulse bg-[linear-gradient(100deg,rgb(255_255_255/0.04)_30%,rgb(255_255_255/0.12)_50%,rgb(255_255_255/0.04)_70%)]"
    />
  )
}

function Gone() {
  return (
    <div className="flex size-full flex-col items-center justify-center gap-2 text-ink-2">
      <FileX className="size-6" />
      <span className="text-xs">Arquivo não existe mais</span>
    </div>
  )
}

function FileCard({ name, size }: { name: string; size: number }) {
  const ext = name.includes('.') ? name.split('.').pop()!.toUpperCase().slice(0, 4) : 'ARQ'
  return (
    <div className="flex size-full items-center gap-3.5 px-5">
      <div className="grid h-16 w-14 shrink-0 place-items-center rounded-[10px] bg-fill-on text-[11px] font-bold tracking-wide">
        {ext}
      </div>
      <div className="flex min-w-0 flex-col">
        <b className="truncate text-[13px]">{name}</b>
        <span className="text-[11px] text-ink-2">{formatSize(size)}</span>
      </div>
    </div>
  )
}

function Report({ result, size }: { result: ResultView; size: Size }) {
  const { shown, more } = shownChanges(result.changes)
  const sum = totals(result.changes)
  if (size === 'card')
    return (
      <div className="flex size-full flex-col gap-1.5 overflow-hidden px-3.5 py-3 text-[11.5px]">
        {result.summary && <span className="text-ink">{result.summary}</span>}
        {shown.map((c) => (
          <Change key={c.path} change={c} />
        ))}
        {more > 0 && (
          <span className="text-ink-3">
            +{more} {more === 1 ? 'arquivo' : 'arquivos'}
          </span>
        )}
      </div>
    )
  return (
    <div className="size-full overflow-y-auto">
      <article className="mx-auto flex max-w-[720px] flex-col gap-6 px-12 pt-11 pb-16 text-[15px]">
        {result.summary && (
          <p className="m-0 text-[19px] leading-snug font-medium tracking-[-0.01em] text-ink">
            {result.summary}
          </p>
        )}
        {result.report && (
          <div className="prose-result">
            <Markdown remarkPlugins={[remarkGfm]} skipHtml>
              {result.report}
            </Markdown>
          </div>
        )}
        {result.changes.length > 0 && (
          <section aria-label="Arquivos alterados" className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between text-[12px] font-semibold tracking-wide text-ink-2 uppercase">
              <span>Arquivos alterados</span>
              <span className="tracking-normal normal-case tabular-nums">
                {result.changes.length} · <span className="text-apple-green">+{sum.added}</span>{' '}
                <span className="text-[#ff6961]">−{sum.removed}</span>
              </span>
            </div>
            <div className="flex flex-col divide-y divide-hairline rounded-xl border border-hairline bg-black/25 px-3.5 font-mono text-[12.5px]">
              {result.changes.map((c) => (
                <div key={c.path} className="py-2">
                  <Change change={c} />
                </div>
              ))}
            </div>
          </section>
        )}
      </article>
    </div>
  )
}

function Change({ change }: { change: ResultView['changes'][number] }) {
  return (
    <div className="flex items-center gap-1.5 tabular-nums">
      <span className="min-w-0 flex-1 truncate text-ink-2">{change.path}</span>
      <span className="text-apple-green">+{change.added}</span>
      <span className="text-[#ff6961]">−{change.removed}</span>
    </div>
  )
}

function MarkdownFile({ id, index, size }: { id: number; index: number; size: Size }) {
  const text = useFileText(id, index)
  if (text.isPending) return <Loading />
  if (text.isError) return <Gone />
  const doc = (
    <Markdown remarkPlugins={[remarkGfm]} skipHtml>
      {cleanMarkdown(text.data)}
    </Markdown>
  )
  if (size === 'card')
    return (
      <div className="prose-result relative size-full overflow-hidden px-3.5 py-3 text-[10.5px]">
        {doc}
        <div className="absolute inset-x-0 bottom-0 h-10 bg-[linear-gradient(transparent,#0e0e11)]" />
      </div>
    )
  return (
    <div className="size-full overflow-y-auto">
      <article className="prose-result mx-auto max-w-[720px] px-12 pt-11 pb-16 text-[15px]">
        {doc}
      </article>
    </div>
  )
}

function TextFile({ id, index }: { id: number; index: number }) {
  const text = useFileText(id, index)
  if (text.isPending) return <Loading />
  if (text.isError) return <Gone />
  return (
    <pre className="m-0 size-full overflow-auto px-4 py-3 font-mono text-[11.5px] leading-relaxed text-ink-2">
      {text.data}
    </pre>
  )
}

/** Gap around the pages in the expanded view, and the widest a page gets there. */
const PAGE_PAD = 48
const PAGE_MAX = 900

function Pdf({ url, size }: { url: string; size: Size }) {
  const pdf = usePdf(url)
  const box = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const el = box.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [pdf.isSuccess])

  if (pdf.isPending) return <Loading />
  if (pdf.isError) return <FileCard name="PDF" size={0} />
  const card = size === 'card'
  const pages = card ? 1 : pdf.data.numPages
  const pageWidth = card
    ? Math.max(0, width - 24)
    : Math.min(PAGE_MAX, Math.max(0, width - PAGE_PAD * 2))
  return (
    <div
      ref={box}
      className={`flex size-full flex-col items-center gap-5 bg-[#0c0c0e] ${card ? 'overflow-hidden pt-3' : 'overflow-y-auto py-8'}`}
    >
      {pageWidth > 0 &&
        Array.from({ length: pages }, (_, i) => (
          <PdfPage key={i} pdf={pdf.data} page={i + 1} width={pageWidth} />
        ))}
    </div>
  )
}

type PdfDoc = NonNullable<ReturnType<typeof usePdf>['data']>

function PdfPage({ pdf, page, width }: { pdf: PdfDoc; page: number; width: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const [ratio, setRatio] = useState(1.414)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let stopped = false
    let task: { cancel: () => void } | null = null
    void pdf
      .getPage(page)
      .then((p) => {
        const el = canvas.current
        if (stopped || !el) return
        const base = p.getViewport({ scale: 1 })
        setRatio(base.height / base.width)
        const viewport = p.getViewport({ scale: (width / base.width) * devicePixelRatio })
        el.width = Math.floor(viewport.width)
        el.height = Math.floor(viewport.height)
        const render = p.render({ canvas: el, viewport })
        task = render
        return render.promise
      })
      .catch((e: unknown) => {
        // A cancelled render (resize, unmount, StrictMode's second run) is not a broken page.
        if (!stopped && (e as { name?: string })?.name !== 'RenderingCancelledException')
          setFailed(true)
      })
    return () => {
      stopped = true
      task?.cancel()
    }
  }, [pdf, page, width])
  if (failed) return null
  return (
    <canvas
      ref={canvas}
      aria-label={`Página ${page}`}
      style={{ width, height: width * ratio }}
      className="shrink-0 rounded-[4px] bg-white shadow-[0_8px_30px_rgb(0_0_0/0.5)]"
    />
  )
}
