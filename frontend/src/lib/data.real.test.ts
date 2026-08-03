// Guards the caption in section 01 against the actual committed board: if a data
// refresh changes the reshuffle, this fails instead of the page lying.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { Flight, aggregateOwners, reshuffleStats } from './data'

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
