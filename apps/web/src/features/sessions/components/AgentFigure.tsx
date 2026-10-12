import type { Look } from '../lib/look'
import { Butler } from './butler/Butler'
import { Messenger } from './butler/Messenger'

/** The session's pixel character; size it with className (it keeps its 36:32 ratio). */
export function AgentFigure({ look, className }: { look: Look; className?: string }) {
  return look.figure === 'butler' ? (
    <Butler state={look.state} className={className} />
  ) : (
    <Messenger state={look.state} className={className} />
  )
}
