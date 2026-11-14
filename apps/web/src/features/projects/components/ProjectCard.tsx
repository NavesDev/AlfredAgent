import { Link } from 'react-router'
import type { Project, SessionView } from '../../../api/events'
import { SessionPhoto } from '../../../components/SessionPhoto'
import { plural } from '../lib/projects'
import { ProjectMark } from './ProjectMark'

/** A project as an album: the cover joins its mark and session photos, then name and counts. */
export function ProjectCard({
  project: p,
  sessions,
}: {
  project: Project
  sessions: SessionView[]
}) {
  const working = sessions.filter((s) => s.status === 'busy').length
  return (
    <Link
      to={`/projects/${p.id}`}
      className="grid overflow-hidden rounded-card bg-white/[0.06] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)] transition hover:scale-[1.02] hover:bg-white/10 motion-reduce:hover:scale-100"
    >
      <div className="relative flex h-32 items-start justify-between bg-[linear-gradient(160deg,rgba(255,255,255,0.1),rgba(255,255,255,0.02))] p-3.5">
        <ProjectMark name={p.name} />
        <span className="absolute right-3.5 bottom-3.5 flex">
          {sessions.slice(0, 4).map((s) => (
            <span
              key={s.name}
              className="-ml-2.5 rounded-full shadow-[0_0_0_2px_rgb(28_28_32/0.9)]"
            >
              <SessionPhoto session={s} size={38} />
            </span>
          ))}
        </span>
        {working > 0 && (
          <span className="absolute bottom-3.5 left-3.5 rounded-full bg-apple-teal/20 px-2.5 py-1 text-[11.5px] font-semibold text-apple-teal">
            {working} trabalhando
          </span>
        )}
      </div>
      <div className="grid gap-0.5 px-3.5 pt-3 pb-3.5">
        <span className="text-base font-semibold">{p.name}</span>
        {p.description && (
          <span className="line-clamp-2 text-[12.5px] text-ink-2">{p.description}</span>
        )}
        <span className="text-xs text-ink-3">
          {p.aliases.length ? `Também: ${p.aliases.join(', ')}` : 'Sem apelidos'}
        </span>
        <span className="mt-1.5 text-xs text-ink-3">
          {plural(p.workspaces.length, 'ambiente', 'ambientes')} ·{' '}
          {plural(sessions.length, 'sessão', 'sessões')}
        </span>
      </div>
    </Link>
  )
}
