import type { CSSProperties, ReactNode } from 'react'
import type { ActivityAction } from '../../../../api/events'
import { C, R } from '../../../../components/pixels'
import './scenes.css'

// Alfred's activity cards: a small pixel-art scene per kind of step, on a 48×22 grid, in the
// staff's palette with amber for what is happening now. Motion lives in scenes.css.

/** An animation from scenes.css, turning around a point of the 48×22 grid when given one. */
const anim = (animation: string, origin?: string): CSSProperties => ({
  animation,
  transformOrigin: origin,
})

const Envelope = ({ x, y }: { x: number; y: number }) => (
  <>
    {R(x, y, 9, 6, C.hi)}
    <path
      d={`M${x} ${y} L${x + 4.5} ${y + 3.5} L${x + 9} ${y}`}
      fill="none"
      stroke={C.mid}
      strokeWidth={0.4}
    />
    {R(x + 3.8, y + 2.6, 1.4, 1.4, C.purple)}
  </>
)

const Quill = () => (
  <>
    <path d="M0 0 L7 -7 L8 -6 L1 1 Z" fill={C.purple2} />
    <path d="M0 0 L-1 1.5 L1 1 Z" fill={C.hat} />
  </>
)

const Gear = ({ cx, cy, r, dir }: { cx: number; cy: number; r: number; dir: 1 | -1 }) => (
  <g
    style={anim(
      `sc-spin ${dir > 0 ? 3 : 2}s linear infinite ${dir < 0 ? 'reverse' : ''}`,
      `${cx}px ${cy}px`,
    )}
  >
    {[0, 45, 90, 135].map((deg) => (
      <rect
        key={deg}
        x={cx - 1}
        y={cy - r - 1.5}
        width={2}
        height={2 * r + 3}
        fill={C.mid}
        transform={`rotate(${deg} ${cx} ${cy})`}
      />
    ))}
    <circle cx={cx} cy={cy} r={r} fill={C.mid} />
    <circle cx={cx} cy={cy} r={r / 2.5} fill={C.black} />
  </g>
)

const Calendar = ({ children }: { children?: ReactNode }) => (
  <>
    {R(13, 3, 20, 17, C.paper)}
    {R(13, 3, 20, 5, C.purple)}
    {Array.from({ length: 15 }, (_, i) =>
      R(15 + (i % 5) * 3.4, 10 + Math.floor(i / 5) * 3, 2.4, 2, i === 7 ? C.amber : C.dim, {
        key: i,
      }),
    )}
    {children}
    {R(16, 1.5, 1.4, 3, C.mid)}
    {R(28.6, 1.5, 1.4, 3, C.mid)}
  </>
)

const Globe = () => {
  const land = (o: number) => (
    <g key={o}>
      {R(o + 9, 6, 4, 2, C.blue2)}
      {R(o + 8, 8, 5, 3, C.blue2)}
      {R(o + 10, 11, 2, 2, C.blue2)}
      {R(o + 16, 9, 3, 4, C.blue2)}
      {R(o + 17, 13, 2, 3, C.blue2)}
      {R(o + 5, 13, 3, 2, C.blue2)}
    </g>
  )
  return (
    <>
      <defs>
        <clipPath id="sc-globe">
          <circle cx={20} cy={11} r={8} />
        </clipPath>
      </defs>
      <circle cx={20} cy={11} r={8.6} fill={C.mid} />
      <g clipPath="url(#sc-globe)">
        {R(10, 2, 20, 18, C.blue)}
        <g style={anim('sc-drift 3s linear infinite')}>{[0, 16, 32].map(land)}</g>
      </g>
    </>
  )
}

const SCENES: Record<ActivityAction, ReactNode> = {
  web_search: (
    <>
      <Globe />
      <g style={anim('sc-sweep 2.4s ease-in-out infinite')}>
        <circle cx={17} cy={9} r={3.6} fill={C.amber2} fillOpacity={0.18} stroke={C.amber} />
        {R(19.5, 11.5, 1.4, 1.4, C.amber)}
        {R(20.8, 12.8, 1.4, 1.4, C.amber)}
        {R(22.1, 14.1, 1.6, 1.6, C.amber)}
      </g>
      {R(34, 4, 10, 6, C.hi)}
      {R(35, 10, 2, 1, C.hi)}
      <text
        x={36.4}
        y={9}
        fontSize={5}
        fill={C.black}
        fontFamily="monospace"
        fontWeight="bold"
        style={anim('sc-blink 1s steps(1) infinite')}
      >
        ?
      </text>
    </>
  ),
  web_page: (
    <>
      {R(10, 3, 28, 17, C.paper)}
      {R(8, 1, 32, 2.4, C.head)}
      {R(8, 19.4, 32, 2.4, C.head)}
      {[5, 8, 11, 14, 17].map((y, i) => R(13, y, [20, 16, 22, 14, 18][i], 1, C.mid, { key: y }))}
      <g style={anim('sc-read 2.5s steps(4) infinite')}>
        {R(12, 4, 24, 3, C.amber, { opacity: 0.3 })}
        <circle
          cx={38}
          cy={5.5}
          r={2.6}
          fill={C.hi}
          fillOpacity={0.25}
          stroke={C.hat}
          strokeWidth={0.8}
        />
        {R(40.4, 6, 0.6, 4, C.hat)}
      </g>
    </>
  ),
  email_read: (
    <>
      {R(6, 17, 36, 3, C.dim)}
      {R(6, 20, 36, 1, C.hat)}
      {R(9, 11, 14, 8, C.head)}
      {R(25, 11, 14, 8, C.head)}
      <g style={anim('sc-fly-in 2.4s ease-out infinite')}>{R(27, 9, 13, 8, C.mid)}</g>
      <g style={anim('sc-rise 2.4s ease-in-out infinite')}>
        {R(17, 6, 12, 7, C.paper)}
        {R(19, 8, 8, 0.6, C.mid)}
        {R(19, 10, 6, 0.6, C.mid)}
      </g>
      {R(15, 8, 16, 10, C.hi)}
      <path d="M15 18 L23 12 L31 18" fill="none" stroke={C.mid} strokeWidth={0.5} />
      <g style={anim('sc-flap 2.4s ease-in-out infinite', '23px 8px')}>
        <path d="M15 8 L23 13 L31 8Z" fill={C.paper} />
        {R(22, 10.5, 2, 2, C.purple)}
      </g>
    </>
  ),
  email_send: (
    <>
      {R(4, 17, 14, 3, C.dim)}
      {R(4, 20, 14, 1, C.hat)}
      <g style={anim('sc-send 2.2s ease-in infinite')}>
        <Envelope x={8} y={10} />
        <g style={anim('sc-flutter 0.3s steps(1) infinite', '8px 11px')}>
          {R(5, 9, 3, 1, C.hi)}
          {R(6, 8, 2, 1, C.hi)}
        </g>
      </g>
      {[0, 1, 2].map((i) =>
        R(22 + i * 5, 14 - i * 3, 2, 0.6, C.amber, {
          key: i,
          style: anim(`sc-blink 0.9s ${i * 0.2}s steps(1) infinite`),
        }),
      )}
    </>
  ),
  calendar_read: (
    <>
      <Calendar>
        <g style={anim('sc-tear 2.2s ease-in infinite', '23px 3px')}>
          {R(13, 3, 20, 17, C.hi)}
          {R(13, 3, 20, 5, C.purple2)}
          <text
            x={20}
            y={16.5}
            fontSize={7}
            fill={C.black}
            fontFamily="monospace"
            fontWeight="bold"
          >
            12
          </text>
        </g>
      </Calendar>
      <circle cx={40} cy={14} r={4} fill={C.hi} stroke={C.mid} strokeWidth={0.6} />
      {R(39.4, 9, 1.2, 1, C.mid)}
      <line
        x1={40}
        y1={14}
        x2={40}
        y2={11.4}
        stroke={C.black}
        strokeWidth={0.6}
        style={anim('sc-spin 1.6s steps(8) infinite', '40px 14px')}
      />
    </>
  ),
  calendar_write: (
    <Calendar>
      <circle
        cx={23}
        cy={14}
        r={3.2}
        fill="none"
        stroke={C.amber}
        strokeWidth={0.6}
        strokeDasharray={21}
        style={anim('sc-draw 2s ease-in-out infinite')}
      />
      <g style={anim('sc-circle 2s ease-in-out infinite', '23px 14px')}>
        <g transform="translate(26 12)">
          <Quill />
        </g>
      </g>
    </Calendar>
  ),
  drive: (
    <>
      {R(14, 1, 20, 20, C.suit)}
      {[2, 8, 14].map((y) => (
        <g key={y} style={y === 8 ? anim('sc-drawer 2.4s ease-in-out infinite') : undefined}>
          {y === 8 && (
            <>
              {R(17, 5, 4, 3, C.paper)}
              {R(22, 4.4, 4, 3.6, C.amber2)}
              {R(27, 5.2, 4, 2.8, C.paper)}
            </>
          )}
          {R(15, y, 18, 5, C.head)}
          {R(22, y + 2, 4, 1, C.silver)}
        </g>
      ))}
    </>
  ),
  browser: (
    <>
      {R(6, 2, 36, 18, C.head)}
      {R(6, 2, 36, 3, C.suit)}
      {[8, 10, 12].map((x) => R(x, 3, 1, 1, C.mid, { key: x }))}
      {R(7, 5, 34, 14, C.black)}
      {R(9, 7, 14, 2, C.dim)}
      {R(9, 11, 20, 1, C.dim)}
      {R(9, 13, 16, 1, C.dim)}
      {R(29, 13, 9, 3, C.amber)}
      <circle
        cx={33.5}
        cy={14.5}
        r={2}
        fill="none"
        stroke={C.amber2}
        strokeWidth={0.4}
        style={anim('sc-click 2.4s ease-out infinite', '33.5px 14.5px')}
      />
      <g style={anim('sc-cursor 2.4s ease-in-out infinite')}>
        <path
          d="M33 15 L33 21 L34.6 19.6 L36 22 L37 21.5 L35.8 19.2 L38 19Z"
          fill={C.hi}
          stroke={C.black}
          strokeWidth={0.3}
        />
      </g>
    </>
  ),
  delegate: (
    <>
      {[0, 1, 2].map((i) =>
        R(4 + i * 2, 10 + i * 2, 4, 0.5, C.mid, {
          key: i,
          style: anim(`sc-blink 0.6s ${i * 0.15}s steps(1) infinite`),
        }),
      )}
      <g style={anim('sc-deliver 2.2s ease-in-out infinite')}>
        <Envelope x={10} y={9} />
      </g>
      {R(36, 8, 7, 5, C.hat)}
      {R(36, 12, 7, 1, C.suit2)}
      {R(34, 13, 11, 1, C.hat)}
      {R(35, 15, 9, 6, C.head)}
      {R(37, 17, 2, 1, C.hi)}
      {R(41, 17, 2, 1, C.hi)}
    </>
  ),
  session: (
    <>
      {R(8, 17, 32, 3, C.dim)}
      {R(21, 10, 7, 1, C.silver)}
      {R(19, 11, 11, 1, C.silver)}
      {R(18, 12, 13, 2, C.silver)}
      {R(16, 14, 17, 2, C.mid)}
      <g style={anim('sc-press 1.2s ease-in infinite')}>
        {R(23.5, 6, 2, 3, C.silver)}
        {R(22, 3, 5, 3, C.hi)}
      </g>
      {[12, 34].map((x) => (
        <g key={x} style={anim('sc-ring 1.2s ease-out infinite')}>
          {R(x, 9, 1, 3, C.amber)}
          {R(x + (x < 20 ? -2 : 2), 7, 1, 7, C.amber, { opacity: 0.6 })}
        </g>
      ))}
    </>
  ),
  project: (
    <>
      {[
        [8, 5],
        [40, 5],
        [40, 17],
      ].map(([x, y], i) => (
        <g key={i} style={anim(`sc-pop 2.4s ${i * 0.4}s ease-out infinite`, `${x}px ${y}px`)}>
          <line
            x1={24}
            y1={11}
            x2={x}
            y2={y}
            stroke={C.mid}
            strokeWidth={0.4}
            strokeDasharray="1 1"
          />
          {R(x - 1.5, y - 1.5, 3, 3, C.hi)}
        </g>
      ))}
      <path d="M24 4 L31 11 L24 18 L17 11Z" fill={C.black} stroke={C.amber} strokeWidth={1} />
      {R(23, 10, 2, 2, C.amber)}
    </>
  ),
  command: (
    <>
      {R(8, 2, 32, 18, C.suit)}
      {[10, 12, 14].map((x) => R(x, 3, 1, 1, C.mid, { key: x }))}
      {R(9, 5, 30, 14, C.black)}
      {[7, 10, 13].map((y, i) => (
        <g key={y}>
          {R(11, y, 1.5, 1, C.amber)}
          {R(13, y, [18, 12, 22][i], 1, C.mid, {
            style: anim(`sc-type 2.4s ${i * 0.5}s steps(6) infinite`, '13px 0'),
          })}
        </g>
      ))}
      {R(11, 16, 1.5, 1, C.amber)}
      {R(13, 16, 1, 1.4, C.hi, { style: anim('sc-blink 0.8s steps(1) infinite') })}
    </>
  ),
  files_read: (
    <>
      {R(10, 4, 10, 3, C.dim)}
      {R(10, 6, 28, 13, C.dim)}
      <g style={anim('sc-rise 1.8s ease-in-out infinite')}>{R(13, 3, 9, 10, C.paper)}</g>
      <g style={anim('sc-rise 1.8s 0.6s ease-in-out infinite')}>{R(23, 4, 9, 10, C.hi)}</g>
      {R(10, 10, 28, 10, C.head)}
      {R(21, 13, 6, 1, C.mid)}
    </>
  ),
  files_edit: (
    <>
      {R(12, 2, 24, 18, C.paper)}
      {[5, 8, 11, 14].map((y, i) =>
        R(15, y, [16, 12, 18, 10][i], 1, C.mid, {
          key: y,
          style: i === 3 ? anim('sc-type 2s steps(5) infinite', '15px 0') : undefined,
        }),
      )}
      <g style={anim('sc-write 2s steps(5) infinite')}>
        <g transform="translate(16 15)">
          <Quill />
        </g>
      </g>
    </>
  ),
  tool: (
    <>
      <Gear cx={19} cy={12} r={5} dir={1} />
      <Gear cx={30} cy={8} r={3.5} dir={-1} />
    </>
  ),
}

type Props = { action: ActivityAction; still?: boolean; className?: string }

/** The scene for a kind of step; still freezes it (a step already done). */
export function ActivityScene({ action, still, className }: Props) {
  return (
    <svg
      viewBox="0 0 48 22"
      shapeRendering="crispEdges"
      aria-hidden="true"
      className={`${className ?? ''} ${still ? 'sc-still' : ''}`}
    >
      {SCENES[action]}
    </svg>
  )
}
