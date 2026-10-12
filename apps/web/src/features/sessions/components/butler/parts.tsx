import type { ReactNode } from 'react'
import { C, R } from '../../../../components/pixels'
import './butler.css'

// Pixel parts shared by the mansion staff (the butler and the messenger), on a 36×32 grid.
// The suits stay neutral; the bow tie borrows the purple of Alfred's orb.

export type Eyes = 'open' | 'closed' | 'down' | 'wide' | 'happy' | 'x'
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

export const Face = ({ eyes = 'open' as Eyes, monocle = true }) => (
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

export const Torso = () => (
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

export const Arm = ({
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

export const Laptop = () => (
  <>
    {R(4, 22, 23, 2, C.dim)}
    {R(7, 24, 17, 1, C.p1)}
  </>
)

export const Legs = ({ tap = false }) => (
  <>
    {R(13, 21, 2, 3, C.suit)}
    {R(17, 21, 2, 3, C.suit)}
    <g className={tap ? 'bt-tapfoot' : undefined}>{R(12, 24, 3, 1, C.hat)}</g>
    {R(17, 24, 3, 1, C.hat)}
  </>
)

export const Sparkles = ({ cx, cy }: { cx: number; cy: number }) => (
  <g className="bt-sparkle">
    {R(cx - 3, cy - 1, 0.8, 0.8, C.hi)}
    {R(cx + 3, cy - 2, 0.8, 0.8, C.hi)}
    {R(cx + 2.2, cy + 1, 0.6, 0.6, C.hi)}
    {R(cx - 2.4, cy + 1.5, 0.6, 0.6, C.hi)}
  </g>
)

export const ArmForward = ({ y = 15 }) => (
  <>
    {R(21, 15, 3, 3, C.suit)}
    {R(24, y, 4, 2, C.suit)}
    {R(28, y, 2, 2, C.hi)}
  </>
)

export const ArmToHat = ({ y }: { y: number }) => (
  <>
    {R(22, y + 1, 3, 14 - y, C.suit)}
    {R(22, y, 3, 1, C.hi)}
  </>
)
