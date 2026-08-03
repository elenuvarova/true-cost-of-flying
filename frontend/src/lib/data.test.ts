import { describe, expect, it } from 'vitest'
import { OwnerAgg, metricT, rankByMetric, reshuffleStats } from './data'

// Minimal owners modelled on the real board: A burns most fuel, B has huge
// contrails, C net-cools. Ranking by fuel and by combined must differ.
const owner = (o: Partial<OwnerAgg> & { owner: string }): OwnerAgg => ({
  ac_type: 'Boeing 757-200',
  flights: 7,
  fuelT: 0,
  contrailT: 0,
  combinedT: 0,
  warm: 0,
  cool: 0,
  zero: 0,
  bizjet: false,
  proxy: false,
  tier: 'med',
  ...o,
})

const OWNERS: OwnerAgg[] = [
  owner({ owner: 'A', fuelT: 300, contrailT: 5, combinedT: 305 }),
  owner({ owner: 'B', fuelT: 100, contrailT: 150, combinedT: 250 }),
  owner({ owner: 'C', fuelT: 280, contrailT: -60, combinedT: 220 }),
]

describe('metricT', () => {
  it('reads the right field per metric', () => {
    expect(metricT(OWNERS[1], 'fuel')).toBe(100)
    expect(metricT(OWNERS[1], 'combined')).toBe(250)
    expect(metricT(OWNERS[1], 'contrail')).toBe(150)
  })
})

describe('rankByMetric', () => {
  it('orders by fuel', () => {
    expect(rankByMetric(OWNERS, 'fuel').map((o) => o.owner)).toEqual(['A', 'C', 'B'])
  })

  it('orders by combined — a different order', () => {
    expect(rankByMetric(OWNERS, 'combined').map((o) => o.owner)).toEqual(['A', 'B', 'C'])
  })

  it('orders contrails signed, so net-cooling sinks to the bottom', () => {
    expect(rankByMetric(OWNERS, 'contrail').map((o) => o.owner)).toEqual(['B', 'A', 'C'])
  })

  it('does not mutate the input array', () => {
    const before = OWNERS.map((o) => o.owner)
    rankByMetric(OWNERS, 'contrail')
    expect(OWNERS.map((o) => o.owner)).toEqual(before)
  })

  it('keeps tier pinned to the owner, not to the row position', () => {
    const ranked = rankByMetric(OWNERS, 'contrail')
    expect(ranked.find((o) => o.owner === 'B')!.tier).toBe(OWNERS[1].tier)
  })
})

describe('reshuffleStats', () => {
  it('counts how many owners change position', () => {
    const s = reshuffleStats(OWNERS, 'fuel', 'combined')
    expect(s.total).toBe(3)
    expect(s.moved).toBe(2) // B 3rd->2nd, C 2nd->3rd; A stays 1st
  })

  it('names the biggest mover with 1-based positions', () => {
    const s = reshuffleStats(OWNERS, 'fuel', 'combined')
    expect(s.biggest).toEqual({ owner: 'B', from: 3, to: 2 })
  })

  it('reports nothing moved when the metrics agree', () => {
    const s = reshuffleStats(OWNERS, 'combined', 'combined')
    expect(s.moved).toBe(0)
    expect(s.biggest).toBeNull()
  })

  it('handles a single owner', () => {
    const s = reshuffleStats([OWNERS[0]], 'fuel', 'combined')
    expect(s).toEqual({ moved: 0, total: 1, biggest: null })
  })
})
