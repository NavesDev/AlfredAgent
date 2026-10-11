import { useSessions } from '../hooks/useSessions'
import { AgentCard } from './AgentCard'

/** One card per named session Alfred can delegate to. */
export function AgentStrip() {
  const sessions = useSessions()
  if (!sessions.length) return null
  return (
    <section
      aria-label="Sessões"
      className="grid w-full grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3 px-4 pb-4"
    >
      {sessions.map((session) => (
        <AgentCard key={session.name} session={session} />
      ))}
    </section>
  )
}
