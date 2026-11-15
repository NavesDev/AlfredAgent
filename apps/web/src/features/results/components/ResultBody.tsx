import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ResultView } from '../../../api/events'
import { FileX } from '../../../components/icons'
import { useFileText } from '../hooks/useFileText'
import { usePdf } from '../hooks/usePdf'
import { fileUrl, formatSize, shownChanges, totals, type Slide } from '../lib/results'

export type Size = 'card' | 'full'

type Props = { result: ResultView; slide: Slide; size: Size }

/** The body of one slide, by kind: media, document, report or a file card. */
export function ResultBody({ result, slide, size }: Props) {
  if (slide.type === 'report') return <Report result={result} size={size} />
  const { file, index } = slide
  if (!file.exists) return <Gone />
  const url = fileUrl(result.id, index)
  const fit = size === 'card' ? 'object-cover' : 'object-contain'
  switch (file.kind) {
    case 'image':
      return <img src={url} alt={file.name} className={`size-full ${fit}`} />
    case 'video':
      return (
        <video
          src={url}
          aria-label={file.name}
          className={`size-full ${fit}`}
          autoPlay
          loop
          playsInline
          muted={size === 'card'}
          controls={size === 'full'}
        />
      )
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
      return <FileCard name={file.name} size={file.size} />
  }
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
  const list = size === 'card' ? shown : result.changes
  const sum = totals(result.changes)
  return (
    <div
      className={`flex size-full flex-col gap-1.5 overflow-hidden text-[11.5px] ${size === 'card' ? 'px-3 py-2.5' : 'overflow-y-auto p-6 text-sm'}`}
    >
      {result.summary && <span className="text-ink">{result.summary}</span>}
      {size === 'full' && result.report && (
        <div className="prose-result text-ink-2">
          <Markdown remarkPlugins={[remarkGfm]} skipHtml>
            {result.report}
          </Markdown>
        </div>
      )}
      {list.map((c) => (
        <div key={c.path} className="flex items-center gap-1.5 tabular-nums">
          <span className="min-w-0 flex-1 truncate text-ink-2">{c.path}</span>
          <span className="text-apple-green">+{c.added}</span>
          <span className="text-[#ff6961]">−{c.removed}</span>
        </div>
      ))}
      {size === 'card' && more > 0 && (
        <span className="text-ink-3">
          +{more} {more === 1 ? 'arquivo' : 'arquivos'}
        </span>
      )}
      {size === 'full' && result.changes.length > 1 && (
        <span className="pt-1 text-ink-3 tabular-nums">
          {result.changes.length} arquivos, +{sum.added} −{sum.removed}
        </span>
      )}
    </div>
  )
}

function MarkdownFile({ id, index, size }: { id: number; index: number; size: Size }) {
  const text = useFileText(id, index)
  if (text.isPending) return <Loading />
  if (text.isError) return <Gone />
  return (
    <div
      className={`prose-result relative size-full overflow-hidden ${size === 'card' ? 'px-3 py-2.5 text-[11px]' : 'overflow-y-auto p-8 text-sm'}`}
    >
      <Markdown remarkPlugins={[remarkGfm]} skipHtml>
        {text.data}
      </Markdown>
      {size === 'card' && (
        <div className="absolute inset-x-0 bottom-0 h-9 bg-[linear-gradient(transparent,rgb(14_14_18/0.95))]" />
      )}
    </div>
  )
}

function TextFile({ id, index }: { id: number; index: number }) {
  const text = useFileText(id, index)
  if (text.isPending) return <Loading />
  if (text.isError) return <Gone />
  return (
    <pre className="m-0 size-full overflow-auto px-3 py-2.5 font-mono text-[10.5px] leading-normal text-ink-2">
      {text.data}
    </pre>
  )
}

function Pdf({ url, size }: { url: string; size: Size }) {
  const pdf = usePdf(url)
  if (pdf.isPending) return <Loading />
  if (pdf.isError) return <FileCard name="PDF" size={0} />
  const pages = size === 'card' ? 1 : pdf.data.numPages
  return (
    <div
      className={`flex size-full flex-col items-center gap-4 bg-black/35 ${size === 'card' ? 'overflow-hidden pt-2.5' : 'overflow-y-auto py-6'}`}
    >
      {Array.from({ length: pages }, (_, i) => (
        <PdfPage key={i} pdf={pdf.data} page={i + 1} width={size === 'card' ? 130 : 820} />
      ))}
    </div>
  )
}

type PdfDoc = NonNullable<ReturnType<typeof usePdf>['data']>

function PdfPage({ pdf, page, width }: { pdf: PdfDoc; page: number; width: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let task: { cancel: () => void } | null = null
    void pdf.getPage(page).then((p) => {
      const el = canvas.current
      if (!el) return
      const base = p.getViewport({ scale: 1 })
      const viewport = p.getViewport({ scale: (width / base.width) * devicePixelRatio })
      el.width = viewport.width
      el.height = viewport.height
      const render = p.render({ canvas: el, viewport })
      task = render
      render.promise.catch(() => setFailed(true))
    })
    return () => task?.cancel()
  }, [pdf, page, width])
  if (failed) return null
  return (
    <canvas
      ref={canvas}
      aria-label={`Página ${page}`}
      style={{ width }}
      className="shrink-0 rounded-[3px] bg-white shadow-lg"
    />
  )
}
