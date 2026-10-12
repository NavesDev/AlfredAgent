import { useEffect, useState, type ReactNode } from 'react'
import type { ButlerState } from '../../lib/butler'
import { Arm, ArmForward, ArmToHat, Face, Laptop, Legs, Sparkles, Torso, type Eyes } from './parts'
import { C, R } from '../../../../components/pixels'

// The implementation sessions' pixel-art butler. Frames follow the approved mockup.

const Hat = ({ dx = 0, dy = 0 }: { dx?: number; dy?: number }) => (
  <g transform={`translate(${dx},${dy})`}>
    {R(11, 1, 10, 3, C.hat)}
    {R(11, 3, 10, 1, C.band)}
    {R(9, 4, 14, 1, C.hat)}
  </g>
)

const Check = ({
  x,
  y,
  s = 1,
  fill = C.hi,
}: {
  x: number
  y: number
  s?: number
  fill?: string
}) => (
  <>
    {[
      [0, 1],
      [1, 2],
      [2, 1],
      [3, 0],
    ].map(([a, b]) => R(x + a * s, y + b * s, s, s, fill, { key: a }))}
  </>
)

/** Seated at the laptop: hat and face bob, the right arm and extras vary. */
const Seated = ({ eyes, right, extra }: { eyes: Eyes; right: ReactNode; extra?: ReactNode }) => (
  <>
    <g className="bt-bob">
      <Hat />
      <Face eyes={eyes} />
    </g>
    <Torso />
    {extra}
    {right}
    <Laptop />
  </>
)

const Envelope = () => (
  <>
    {R(25, 10.5, 7, 4.5, C.hi)}
    <path d="M25 10.5 L28.5 13 L32 10.5" fill="none" stroke={C.mid} strokeWidth={0.4} />
    {R(27.9, 12.3, 1.3, 1.3, C.purple)}
  </>
)

const Standing = ({
  eyes = 'open' as Eyes,
  right,
  hat = true,
  hatLift = false,
}: {
  eyes?: Eyes
  right: ReactNode
  hat?: boolean
  hatLift?: boolean
}) => (
  <>
    {hat && <Hat dx={hatLift ? 1 : 0} dy={hatLift ? -3 : 0} />}
    <Face eyes={eyes} />
    <Torso />
    <Arm x={8} y={15} />
    {right}
    <Legs />
  </>
)

const HatInHand = ({ trick = false }) => (
  <>
    {R(21, 15, 3, 3, C.suit)}
    {R(24, 17, 4, 2, C.suit)}
    {R(28, 17, 2, 2, C.hi)}
    {R(24, 13, 10, 1, C.hat)}
    {R(25, 14, 8, 3, C.hat)}
    {R(25, 14, 8, 1, C.band)}
    {trick && (
      <>
        <g className="bt-rise">
          <Check x={26.5} y={7} s={1.3} />
        </g>
        <Sparkles cx={29} cy={9} />
        <circle
          className="bt-pop"
          cx={29}
          cy={10}
          r={3}
          fill="none"
          stroke={C.hi}
          strokeWidth={0.4}
        />
      </>
    )}
  </>
)

/* ----- states ------------------------------------------------------------------------------ */

const sleeping = (
  <>
    <g className="bt-breathe">
      <g transform="translate(0,1)">
        <Hat />
        <Face eyes="closed" monocle={false} />
      </g>
      <Torso />
      <Arm x={8} y={17} h={5} />
      <Arm x={21} y={17} h={5} />
    </g>
    <Laptop />
    <text className="bt-z" x={23} y={5} fontSize={4} fill={C.mid} fontFamily="monospace">
      z
    </text>
    <text className="bt-z bt-z2" x={25} y={3} fontSize={3} fill={C.mid} fontFamily="monospace">
      z
    </text>
  </>
)

const editing = (
  <Seated
    eyes="open"
    right={<Arm x={21} className="bt-tap-b" />}
    extra={<Arm x={8} className="bt-tap-a" />}
  />
)

const exploring = (
  <Seated
    eyes="down"
    right={<Arm x={21} className="bt-slow-tap" />}
    extra={
      <>
        <Arm x={8} />
        {R(24.5, 9.5, 0.8, 0.8, C.mid)}
        {R(26, 7.5, 1.2, 1.2, C.mid)}
        <rect x={27} y={0} width={8} height={6.5} rx={1.5} fill={C.hi} />
        <g className="bt-ico">
          {R(29, 2, 4, 3, C.dim)}
          {R(29, 1.4, 1.8, 0.8, C.dim)}
        </g>
        <g className="bt-ico bt-ico2">
          {R(29.5, 1.3, 3, 4, C.dim)}
          {R(30.2, 2.3, 1.6, 0.4, C.hi)}
          {R(30.2, 3.3, 1.6, 0.4, C.hi)}
        </g>
        <g className="bt-ico bt-ico3">
          <circle cx={30.4} cy={2.8} r={1.3} fill="none" stroke={C.dim} strokeWidth={0.6} />
          {R(31.3, 3.8, 0.6, 1.4, C.dim, { transform: 'rotate(-45 31.6 4.5)' })}
        </g>
      </>
    }
  />
)

const RUNNING: Frame[] = [
  [
    <Seated
      key="f0"
      eyes="wide"
      right={
        <>
          {R(21, 8, 3, 9, C.suit)}
          {R(21, 7, 3, 1, C.hi)}
        </>
      }
      extra={<Arm x={8} />}
    />,
    600,
  ],
  [
    <Seated
      key="f1"
      eyes="closed"
      right={
        <>
          <Arm x={21} />
          <circle
            className="bt-press"
            cx={22.5}
            cy={22}
            r={3}
            fill="none"
            stroke={C.hi}
            strokeWidth={0.4}
          />
        </>
      }
      extra={<Arm x={8} />}
    />,
    400,
  ],
  [
    <Seated
      key="f2"
      eyes="open"
      right={null}
      extra={
        <>
          {R(9, 16, 14, 3, C.suit)}
          {R(12, 16.5, 2, 1.5, C.hi)}
          {R(18, 16.5, 2, 1.5, C.hi)}
          {R(25, 4, 1.2, 1.2, C.hi, { className: 'bt-dot' })}
          {R(27, 4, 1.2, 1.2, C.hi, { className: 'bt-dot bt-dot2' })}
          {R(29, 4, 1.2, 1.2, C.hi, { className: 'bt-dot bt-dot3' })}
        </>
      }
    />,
    2200,
  ],
]

const DELEGATING: Frame[] = [
  [
    <Seated
      key="f3"
      eyes="open"
      right={<ArmForward />}
      extra={
        <>
          <Arm x={8} />
          <Envelope />
        </>
      }
    />,
    500,
  ],
  [
    <Seated
      key="f4"
      eyes="happy"
      right={<ArmForward />}
      extra={
        <>
          <Arm x={8} />
          <g className="bt-fly">
            <Envelope />
          </g>
        </>
      }
    />,
    1000,
  ],
]

const DONE: Frame[] = [
  [<Standing key="f5" right={<Arm x={21} y={15} />} />, 350],
  [<Standing key="f6" right={<ArmToHat y={4} />} />, 200],
  [<Standing key="f7" eyes="happy" right={<ArmToHat y={1} />} hatLift />, 200],
  [<Standing key="f8" eyes="happy" hat={false} right={<HatInHand />} />, 400],
  [<Standing key="f9" eyes="wide" hat={false} right={<HatInHand trick />} />, 1300],
  [<Standing key="f10" eyes="happy" right={<ArmToHat y={1} />} hatLift />, 200],
  [<Standing key="f11" eyes="happy" right={<Arm x={21} y={15} />} />, 350],
]

const waiting = (
  <>
    <Hat />
    <Face eyes="down" />
    {R(12, 6.4, 2, 0.6, C.mid)}
    {R(18, 5.6, 2, 0.6, C.mid)}
    <Torso />
    <Arm x={8} y={15} />
    <Legs tap />
    <g className="bt-sway">
      {R(28.6, 7, 0.8, 8, C.mid)}
      {R(24, 0, 10, 7, C.hi)}
      {R(24, 0, 10, 0.6, C.mid)}
      <text x={27.2} y={5.7} fontSize={5.5} fill={C.black} fontFamily="monospace" fontWeight="bold">
        ?
      </text>
    </g>
    <ArmForward />
  </>
)

const queued = (
  <>
    <Hat />
    <Face eyes="down" />
    <Torso />
    <Arm x={8} y={15} />
    <Legs tap />
    <ArmForward />
    <path d="M18 18 Q24 21 29 15" fill="none" stroke={C.silver} strokeWidth={0.3} />
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

const error = (
  <>
    <g className="bt-shake">
      <Hat />
      <Face eyes="x" />
      <Torso />
      <Arm x={8} />
      <Arm x={21} />
    </g>
    <Laptop />
  </>
)

type Frame = [ReactNode, number]

const STILL: Partial<Record<ButlerState, ReactNode>> = {
  sleeping,
  editing,
  exploring,
  waiting,
  queued,
  error,
}
const FRAMES: Partial<Record<ButlerState, { frames: Frame[]; loop: boolean }>> = {
  running: { frames: RUNNING, loop: true },
  delegating: { frames: DELEGATING, loop: false },
  done: { frames: DONE, loop: false },
}

/** Steps through frames on a timer; restarts when the sequence changes. */
function useFrame(sequence: { frames: Frame[]; loop: boolean } | undefined) {
  const [state, setState] = useState({ sequence, i: 0 })
  const i = state.sequence === sequence ? state.i : 0
  if (state.sequence !== sequence) setState({ sequence, i: 0 })
  useEffect(() => {
    if (!sequence) return
    const last = i === sequence.frames.length - 1
    if (last && !sequence.loop) return
    const timer = setTimeout(
      () => setState({ sequence, i: last ? 0 : i + 1 }),
      sequence.frames[i][1],
    )
    return () => clearTimeout(timer)
  }, [sequence, i])
  return sequence ? sequence.frames[i][0] : null
}

type Props = { state: ButlerState; className?: string; title?: string }

/** The butler drawing for a state; size it with className (it keeps its 36:32 ratio). */
export function Butler({ state, className, title }: Props) {
  const frame = useFrame(FRAMES[state])
  return (
    <svg
      viewBox="0 0 36 32"
      shapeRendering="crispEdges"
      className={className}
      role="img"
      aria-label={title}
      style={{ overflow: 'visible' }}
    >
      {frame ?? STILL[state]}
    </svg>
  )
}
