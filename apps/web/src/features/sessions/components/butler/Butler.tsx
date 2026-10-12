import { useEffect, useState, type Key, type ReactNode, type SVGProps } from 'react'
import type { ButlerState } from '../../lib/butler'
import './butler.css'

// The implementation sessions' pixel-art butler, on a 36×32 grid. The suit stays neutral;
// the bow tie borrows the purple of Alfred's orb. Frames follow the approved mockup.

const C = {
  suit: '#34343e',
  suit2: '#45454f',
  head: '#5a5a64',
  hat: '#26262e',
  band: '#45454f',
  mid: '#8a8a93',
  dim: '#4b4b52',
  p1: '#2a2a2f',
  hi: '#e8e8ec',
  paper: '#d9d6cc',
  purple: '#6d4cff',
  purple2: '#8d6cff',
  black: '#0c0c0e',
  silver: '#c8c8cc',
}

type RectProps = Omit<SVGProps<SVGRectElement>, 'x' | 'y' | 'width' | 'height' | 'fill' | 'key'>
const R = (
  x: number,
  y: number,
  w: number,
  h: number,
  fill: string,
  { key, ...props }: RectProps & { key?: Key } = {},
) => <rect key={key} x={x} y={y} width={w} height={h} fill={fill} {...props} />

const Hat = ({ dx = 0, dy = 0 }: { dx?: number; dy?: number }) => (
  <g transform={`translate(${dx},${dy})`}>
    {R(11, 1, 10, 3, C.hat)}
    {R(11, 3, 10, 1, C.band)}
    {R(9, 4, 14, 1, C.hat)}
  </g>
)

type Eyes = 'open' | 'closed' | 'down' | 'wide' | 'happy' | 'x'
const EYES: Record<Eyes, ReactNode> = {
  open: (
    <g className="bt-blink">
      {R(12, 8, 2, 1, C.hi)}
      {R(18, 8, 2, 1, C.hi)}
    </g>
  ),
  closed: (
    <>
      {R(12, 9, 2, 0.6, C.mid)}
      {R(18, 9, 2, 0.6, C.mid)}
    </>
  ),
  down: (
    <>
      {R(12, 9, 2, 1, C.hi)}
      {R(18, 9, 2, 1, C.hi)}
    </>
  ),
  wide: (
    <>
      {R(12, 7, 2, 2, C.hi)}
      {R(18, 7, 2, 2, C.hi)}
    </>
  ),
  happy: (
    <>
      {[12, 14, 18, 20].map((x) => R(x, 8, 1, 1, C.hi, { key: x }))}
      {R(13, 7, 1, 1, C.hi)}
      {R(19, 7, 1, 1, C.hi)}
    </>
  ),
  x: (
    <>
      {[
        [12, 7],
        [13, 8],
        [14, 9],
        [14, 7],
        [12, 9],
        [18, 7],
        [19, 8],
        [20, 9],
        [20, 7],
        [18, 9],
      ].map(([x, y]) => R(x, y, 1, 1, C.hi, { key: `${x}-${y}` }))}
    </>
  ),
}

const Face = ({ eyes = 'open' as Eyes, monocle = true }) => (
  <>
    {R(10, 5, 12, 9, C.head)}
    {EYES[eyes]}
    {monocle && (
      <>
        <rect
          x={17.25}
          y={7.25}
          width={3.5}
          height={2.5}
          fill="none"
          stroke={C.mid}
          strokeWidth={0.5}
        />
        {R(20.5, 9.5, 0.5, 3, C.mid)}
      </>
    )}
    {R(12, 11, 3, 1, C.mid)}
    {R(17, 11, 3, 1, C.mid)}
    {R(15, 10, 2, 1, C.mid)}
  </>
)

const Torso = () => (
  <>
    {R(11, 14, 10, 7, C.suit)}
    {R(14, 14, 4, 6, C.hi)}
    {R(13, 15, 1, 4, C.suit2)}
    {R(18, 15, 1, 4, C.suit2)}
    {R(13, 14, 2, 2, C.purple)}
    {R(17, 14, 2, 2, C.purple)}
    {R(15, 14.5, 2, 1, C.purple2)}
  </>
)

const Arm = ({
  x,
  y = 16,
  h = 6,
  className,
}: {
  x: number
  y?: number
  h?: number
  className?: string
}) => (
  <g className={className}>
    {R(x, y, 3, h, C.suit)}
    {R(x, y + h - 1, 3, 1, C.hi)}
  </g>
)

const Laptop = () => (
  <>
    {R(4, 22, 23, 2, C.dim)}
    {R(7, 24, 17, 1, C.p1)}
  </>
)

const Legs = ({ tap = false }) => (
  <>
    {R(13, 21, 2, 3, C.suit)}
    {R(17, 21, 2, 3, C.suit)}
    <g className={tap ? 'bt-tapfoot' : undefined}>{R(12, 24, 3, 1, C.hat)}</g>
    {R(17, 24, 3, 1, C.hat)}
  </>
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

const Sparkles = ({ cx, cy }: { cx: number; cy: number }) => (
  <g className="bt-sparkle">
    {R(cx - 3, cy - 1, 0.8, 0.8, C.hi)}
    {R(cx + 3, cy - 2, 0.8, 0.8, C.hi)}
    {R(cx + 2.2, cy + 1, 0.6, 0.6, C.hi)}
    {R(cx - 2.4, cy + 1.5, 0.6, 0.6, C.hi)}
  </g>
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

const ArmForward = ({ y = 15 }) => (
  <>
    {R(21, 15, 3, 3, C.suit)}
    {R(24, y, 4, 2, C.suit)}
    {R(28, y, 2, 2, C.hi)}
  </>
)

const ArmToHat = ({ y }: { y: number }) => (
  <>
    {R(22, y + 1, 3, 14 - y, C.suit)}
    {R(22, y, 3, 1, C.hi)}
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
