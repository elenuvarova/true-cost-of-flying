// Guards the caption in section 01 against the actual committed board: if a data
// refresh changes the reshuffle, this fails instead of the page lying.
import { readFileSync, readdirSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { Flight, aggregateOwners, reshuffleStats } from './data'
import { flightLevel, parseTrack } from './track'

const flights: Flight[] = JSON.parse(readFileSync('public/data/leaderboard.json', 'utf8'))

describe('the real board', () => {
  it('has 84 flights across 11 owners', () => {
    expect(flights).toHaveLength(84)
    expect(new Set(flights.map((f) => f.owner_label)).size).toBe(11)
  })

  it('reshuffles 5 of 11 at GWP100 when fuel becomes combined', () => {
    const s = reshuffleStats(aggregateOwners(flights, 'GWP100'), 'fuel', 'combined')
    expect(s).toMatchObject({ moved: 5, total: 11 })
    expect(s.biggest).toEqual({ owner: 'Eric Schmidt', from: 7, to: 4 })
  })

  it('reshuffles 6 of 11 at GWP20', () => {
    const s = reshuffleStats(aggregateOwners(flights, 'GWP20'), 'fuel', 'combined')
    expect(s).toMatchObject({ moved: 6, total: 11 })
    expect(s.biggest).toEqual({ owner: 'Eric Schmidt', from: 7, to: 3 })
  })

  it('carries the night classification exported in task 3', () => {
    expect(flights.every((f) => f.night_class !== undefined)).toBe(true)
    const classes = new Set(flights.map((f) => f.night_class))
    expect(classes).toContain('night')
    expect(classes).toContain('day')
  })
})

const readTrack = (id: string) =>
  parseTrack(JSON.parse(readFileSync(`public/data/tracks/${id}.geojson`, 'utf8')))

// Standard median: average the two middle values on an even-length sample.
// (Taking the upper middle instead reports 158 rather than 155.5 here, which
// would put the section-03 copy a couple of segments out.)
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  const mid = s.length / 2
  return s.length % 2 ? s[Math.floor(mid)] : (s[mid - 1] + s[mid]) / 2
}

describe('a real exported track', () => {
  it('shows Taylor Swift 2024-12-10 concentrating all forcing in one segment', () => {
    const t = readTrack('a81b13_20241210')
    expect(t.segments.length).toBe(169)
    expect(t.nonZero).toBe(1)
    expect(t.peakIndex).toBeGreaterThanOrEqual(0)
  })

  it('recovers altitude for the Trump 2025-02-14 flight (FL401)', () => {
    const t = readTrack('aa3410_20250214')
    expect(flightLevel(t.maxAltM)).toBeGreaterThanOrEqual(395)
    expect(flightLevel(t.maxAltM)).toBeLessThanOrEqual(405)
  })

  it('keeps the concentration claim section 03 makes: 30 flights, median 8 live segments of ~156', () => {
    const ids = readdirSync('public/data/tracks').map((f) => f.replace('.geojson', ''))
    const formed = ids.map(readTrack).filter((t) => t.nonZero > 0)
    expect(formed.length).toBe(30)
    expect(median(formed.map((t) => t.nonZero))).toBe(8)
    expect(Math.round(median(formed.map((t) => t.segments.length)))).toBe(156)
  })

  it('keeps the claim that the top five segments carry ~95% of the effect', () => {
    const ids = readdirSync('public/data/tracks').map((f) => f.replace('.geojson', ''))
    const shares = ids
      .map(readTrack)
      .filter((t) => t.totalAbsEfJ > 0)
      .map((t) => {
        const top5 = t.segments
          .map((s) => Math.abs(s.efJ))
          .sort((a, b) => b - a)
          .slice(0, 5)
          .reduce((a, b) => a + b, 0)
        return (100 * top5) / t.totalAbsEfJ
      })
    // A median, not a floor: the weakest flight concentrates only 23% in its
    // top five, so section 03's copy must say "median".
    expect(median(shares)).toBeGreaterThan(94)
    expect(median(shares)).toBeLessThan(97)
  })
})
