import { describe, expect, it } from 'vitest'
import type { RateLimit } from '../../../api/events'
import { headline, percentOf, readAgo, resetsIn, sortLimits, toneOf, windowShort } from './usage'

const limit = (over: Partial<RateLimit>): RateLimit => ({
  window: 'five_hour',
  status: 'allowed',
  utilization: null,
  resets_at: null,
  read_at: 0,
  ...over,
})

describe('usage', () => {
  it('colors by how close the window is to its limit', () => {
    expect(toneOf(limit({ utilization: 0.3 }))).toBe('ok')
    expect(toneOf(limit({ utilization: 0.85 }))).toBe('warn')
    expect(toneOf(limit({ status: 'allowed_warning' }))).toBe('warn')
    expect(toneOf(limit({ status: 'rejected', utilization: 0.2 }))).toBe('bad')
  })

  it('heads with a blocked window, else the fullest, else the 5-hour one', () => {
    const week = limit({ window: 'seven_day', utilization: 0.9 })
    const five = limit({ window: 'five_hour', utilization: 0.4 })
    expect(headline([five, week])).toBe(week)
    const opus = limit({ window: 'seven_day_opus', status: 'rejected' })
    expect(headline([five, week, opus])).toBe(opus)
    const bare = limit({ window: 'seven_day' })
    expect(headline([bare, limit({})])?.window).toBe('five_hour')
    expect(headline([])).toBeNull()
  })

  it('formats shares, windows and times', () => {
    expect(percentOf(limit({ utilization: 0.724 }))).toBe(72)
    expect(percentOf(limit({}))).toBeNull()
    expect(windowShort('five_hour')).toBe('5h')
    expect(sortLimits([limit({ window: 'seven_day' }), limit({})]).map((l) => l.window)).toEqual([
      'five_hour',
      'seven_day',
    ])
    const now = 1_000_000 * 1000
    expect(resetsIn(1_000_000 + 2 * 3600 + 600, now)).toBe('reinicia em 2 h 10 min')
    expect(resetsIn(1_000_000 - 5, now)).toBe('já reiniciou')
    expect(resetsIn(null, now)).toBeNull()
    expect(readAgo(1_000_000 - 20, now)).toBe('lido agora')
    expect(readAgo(1_000_000 - 180, now)).toBe('lido há 3 min')
  })
})
