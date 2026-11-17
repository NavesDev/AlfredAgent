import type { ResultView } from '../../../api/events'
import { FileText, FileX } from '../../../components/icons'
import { useResultActions } from '../hooks/useResultActions'
import { useResults } from '../hooks/useResults'
import { fileUrl, timeLabel, totals } from '../lib/results'

/** A session's results under its card; clicking one shows it again as a card. */
export function ResultHistory({ session, local }: { session: string; local: boolean }) {
  const results = useResults(session)
  const { present } = useResultActions()
  return (
    <section aria-label="Resultados" className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold tracking-wide text-ink-2 uppercase">Resultados</h3>
        <span className="text-xs text-ink-3">últimos 30</span>
      </div>
      <ResultList
        results={results.data ?? []}
        local={local}
        onShow={(id) => present.mutate({ id, mode: 'ampliado' })}
      />
    </section>
  )
}

export function ResultList({
  results,
  local = true,
  onShow,
}: {
  results: ResultView[]
  local?: boolean
  onShow: (id: number) => void
}) {
  if (results.length === 0)
    return (
      <p className="m-0 rounded-2xl bg-well px-3 py-3 text-xs text-ink-2">Nenhum resultado ainda</p>
    )
  return (
    <ul className="m-0 flex list-none flex-col divide-y divide-hairline rounded-2xl bg-well p-0">
      {results.map((r) => (
        <li key={r.id}>
          <Row result={r} local={local} onShow={() => onShow(r.id)} />
        </li>
      ))}
    </ul>
  )
}

function Row({
  result,
  local,
  onShow,
}: {
  result: ResultView
  local: boolean
  onShow: () => void
}) {
  const when = timeLabel(result.created_at)
  const gone =
    result.report === null && result.files.length > 0 && result.files.every((f) => !f.exists)
  const image = result.files.findIndex((f) => f.exists && f.kind === 'image')
  const sum = totals(result.changes)
  const thumb = 'grid size-11 shrink-0 place-items-center overflow-hidden rounded-[10px] bg-fill'
  const detail = gone ? (
    `Arquivo não existe mais · ${when}`
  ) : result.report !== null ? (
    <>
      Relatório
      {result.changes.length > 0 && (
        <>
          {' · '}
          <span className="text-apple-green">+{sum.added}</span>{' '}
          <span className="text-[#ff6961]">−{sum.removed}</span>
        </>
      )}
      {` · ${when}`}
    </>
  ) : (
    `${result.files[0]?.name ?? ''} · ${when}`
  )
  const body = (
    <>
      <span className={thumb}>
        {gone ? (
          <FileX className="size-5" />
        ) : local && image >= 0 ? (
          <img src={fileUrl(result.id, image)} alt="" className="size-full object-cover" />
        ) : (
          <FileText className="size-5" />
        )}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <b className="truncate text-[13px] font-semibold">{result.title}</b>
        <span className="truncate text-xs text-ink-2 tabular-nums">{detail}</span>
      </span>
    </>
  )
  if (gone) return <div className="flex items-center gap-3 px-3 py-2.5 opacity-55">{body}</div>
  return (
    <button
      type="button"
      onClick={onShow}
      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition hover:bg-fill"
    >
      {body}
      <span className="text-xs text-ink-2">Mostrar</span>
    </button>
  )
}
