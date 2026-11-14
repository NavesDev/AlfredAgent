import type { SessionView } from '../api/events'
import { gradientFor, initials, presence, type Tone } from '../lib/presence'

const RING: Record<Tone, string> = {
  work: 'after:border-apple-teal after:border-x-transparent after:animate-spin-slow',
  queue: 'after:border-apple-orange',
  error: 'after:border-apple-red',
  idle: 'after:border-transparent',
  sleep: 'after:border-transparent',
}

type Props = {
  session: SessionView
  size: number
  /** Generated portrait; until it exists the session shows its initials. */
  src?: string | null
}

/** A session's photo: portrait or monogram, ringed by what it is doing. */
export function SessionPhoto({ session, size, src }: Props) {
  const { tone } = presence(session)
  const [from, to] = gradientFor(session.name)
  return (
    <span
      data-tone={tone}
      style={{ width: size, height: size }}
      className={`relative inline-grid shrink-0 place-items-center rounded-full after:absolute after:-inset-[3px] after:rounded-full after:border-2 ${RING[tone]}`}
    >
      {src ? (
        <img
          src={src}
          alt={`Retrato de ${session.name}`}
          className="size-full rounded-full object-cover"
        />
      ) : (
        <span
          aria-hidden
          style={{ background: `linear-gradient(180deg, ${from}, ${to})`, fontSize: size * 0.36 }}
          className="grid size-full place-items-center rounded-full font-semibold text-white"
        >
          {initials(session.name)}
        </span>
      )}
    </span>
  )
}
