import { createElement, type Key, type SVGProps } from 'react'

// The pixel-art palette (the staff and Alfred's activity cards) and the one-pixel-rect helper
// every drawing is made of.

export const C = {
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
  amber: '#fbbf24',
  amber2: '#fde68a',
  blue: '#22307a',
  blue2: '#3d56c4',
}

type RectProps = Omit<SVGProps<SVGRectElement>, 'x' | 'y' | 'width' | 'height' | 'fill' | 'key'>
export const R = (
  x: number,
  y: number,
  w: number,
  h: number,
  fill: string,
  { key, ...props }: RectProps & { key?: Key } = {},
) => createElement('rect', { key, x, y, width: w, height: h, fill, ...props })
