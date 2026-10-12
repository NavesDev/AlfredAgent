import type { ReactNode } from 'react'
import type { MessengerState } from '../../lib/messenger'
import { Arm, ArmForward, ArmToHat, Face, Laptop, Legs, Sparkles, Torso, type Eyes } from './parts'
import { C, R } from './pixels'

// The general sessions' messenger: the butler's face under a pillbox cap, without the monocle,
// running errands with a tray instead of typing at a laptop.

const Cap = () => (
  <>
    {R(12, 1, 8, 4, C.hat)}
    {R(12, 3, 8, 1, C.purple)}
    {R(15, 0, 2, 1, C.mid)}
  </>
)

const Head = ({ eyes }: { eyes: Eyes }) => (
  <>
    <Cap />
    <Face eyes={eyes} monocle={false} />
  </>
)

const sleeping = (
  <>
    <g className="bt-breathe">
      <g transform="translate(0,1)">
        <Head eyes="closed" />
      </g>
      <Torso />
      <Arm x={8} y={17} h={5} />
      <Arm x={21} y={17} h={5} />
    </g>
    <Laptop />
    {R(25, 20, 4, 2, C.silver)}
    {R(26.5, 19, 1, 1, C.silver)}
    <text className="bt-z" x={23} y={5} fontSize={4} fill={C.mid} fontFamily="monospace">
      z
    </text>
    <text className="bt-z bt-z2" x={25} y={3} fontSize={3} fill={C.mid} fontFamily="monospace">
      z
    </text>
  </>
)

const carrying = (
  <>
    <g className="bt-bob">
      <Head eyes="open" />
      <Torso />
      <Arm x={8} y={15} className="bt-swing" />
      {R(22, 9, 3, 6, C.suit)}
      {R(22, 8, 3, 1, C.hi)}
      {R(18, 7, 11, 1, C.silver)}
      {R(20, 4, 7, 3, C.silver)}
      {R(23, 3, 1, 1, C.silver)}
    </g>
    <g className="bt-walk-a">
      {R(13, 21, 2, 3, C.suit)}
      {R(12, 24, 3, 1, C.hat)}
    </g>
    <g className="bt-walk-b">
      {R(17, 21, 2, 3, C.suit)}
      {R(17, 24, 3, 1, C.hat)}
    </g>
  </>
)

const queued = (
  <>
    <Head eyes="down" />
    <Torso />
    <Arm x={8} y={15} />
    <Legs tap />
    <ArmForward />
    <circle cx={30} cy={13} r={2} fill={C.hi} stroke={C.mid} strokeWidth={0.4} />
    {R(29.6, 10.4, 0.8, 0.6, C.mid)}
    <line
      className="bt-tick"
      x1={30}
      y1={13}
      x2={30}
      y2={11.6}
      stroke={C.black}
      strokeWidth={0.4}
    />
  </>
)

const done = (
  <>
    <g className="bt-hop">
      <Head eyes="happy" />
      <Torso />
      <Arm x={8} y={15} />
      <ArmToHat y={3} />
      <Legs />
    </g>
    <Sparkles cx={29} cy={4} />
  </>
)

const error = (
  <>
    <g className="bt-shake">
      <Head eyes="x" />
      <Torso />
      <Arm x={8} y={15} />
      <Arm x={21} y={15} />
      <Legs />
    </g>
    {/* the tray flat on the floor, the cloche tipped on its side over it */}
    {R(21, 24, 10, 1, C.silver)}
    {R(21, 24.6, 10, 0.4, C.mid)}
    {R(23, 23, 2, 1, C.paper)}
    {R(28.5, 19.5, 0.5, 4.5, C.mid)}
    {R(29, 20, 2, 4, C.silver)}
    {R(31, 20.5, 1, 3, C.silver)}
    {R(32, 21.5, 1, 1, C.silver)}
  </>
)

const STATES: Record<MessengerState, ReactNode> = { sleeping, carrying, queued, done, error }

type Props = { state: MessengerState; className?: string; title?: string }

/** The messenger drawing for a state; size it with className (it keeps its 36:32 ratio). */
export function Messenger({ state, className, title }: Props) {
  return (
    <svg
      viewBox="0 0 36 32"
      shapeRendering="crispEdges"
      className={className}
      role="img"
      aria-label={title}
      style={{ overflow: 'visible' }}
    >
      {STATES[state]}
    </svg>
  )
}
