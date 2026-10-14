import type { CSSProperties } from 'react'
import type { Look } from '../lib/look'
import { Butler } from './butler/Butler'
import { Messenger } from './butler/Messenger'

type Props = { look: Look; className?: string; style?: CSSProperties }

/** The session's pixel character; size it with className or style (it keeps its 36:32 ratio). */
export function AgentFigure({ look, className, style }: Props) {
  const figure =
    look.figure === 'butler' ? (
      <Butler state={look.state} className="block size-full" />
    ) : (
      <Messenger state={look.state} className="block size-full" />
    )
  return (
    <span className={`block ${className ?? ''}`} style={style}>
      {figure}
    </span>
  )
}
