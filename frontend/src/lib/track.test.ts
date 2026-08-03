import { describe, expect, it } from 'vitest'
import { flightLevel, parseTrack } from './track'

const seg = (lon: number, lat: number, alt: number, ef_tj: number, ef_share = 0) => ({
  type: 'Feature',
  geometry: { type: 'LineString', coordinates: [[lon, lat, alt], [lon + 1, lat + 1, alt]] },
  properties: { ef_tj, ef_share },
})

const track = (...features: unknown[]) => ({ type: 'FeatureCollection', features })

describe('parseTrack', () => {
  it('converts terajoules back to joules', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 44.761)))
    expect(t.segments[0].efJ).toBeCloseTo(4.4761e13, -8)
  })

  it('keeps the sign of a cooling segment', () => {
    const t = parseTrack(track(seg(0, 0, 11000, -12.5)))
    expect(t.segments[0].efJ).toBeLessThan(0)
  })

  it('uses the segment midpoint for position', () => {
    const t = parseTrack(track(seg(-10, 40, 11000, 0)))
    expect(t.segments[0].lon).toBeCloseTo(-9.5)
    expect(t.segments[0].lat).toBeCloseTo(40.5)
  })

  it('averages altitude across the segment points', () => {
    const f = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0, 10000], [1, 1, 12000]] },
      properties: { ef_tj: 0, ef_share: 0 },
    }
    expect(parseTrack(track(f)).segments[0].altM).toBe(11000)
  })

  it('finds the peak by absolute forcing, so a big cooling segment wins', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 5), seg(1, 1, 11000, -90), seg(2, 2, 11000, 10)))
    expect(t.peakIndex).toBe(1)
  })

  it('sums absolute forcing and counts non-zero segments', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 5), seg(1, 1, 11000, -10), seg(2, 2, 11000, 0)))
    expect(t.totalAbsEfJ).toBeCloseTo(1.5e13, -8)
    expect(t.nonZero).toBe(2)
  })

  it('reports the maximum altitude reached', () => {
    const t = parseTrack(track(seg(0, 0, 8000, 0), seg(1, 1, 12215, 0)))
    expect(t.maxAltM).toBe(12215)
  })

  it('indexes segments in file order', () => {
    const t = parseTrack(track(seg(0, 0, 1, 0), seg(1, 1, 1, 0), seg(2, 2, 1, 0)))
    expect(t.segments.map((s) => s.index)).toEqual([0, 1, 2])
  })

  it('survives an empty or malformed track', () => {
    expect(parseTrack(null)).toEqual({ segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 })
    expect(parseTrack(track({ type: 'Feature', geometry: { type: 'Point', coordinates: [0, 0] } })).segments).toHaveLength(0)
  })

  it('tolerates 2-element coordinates from an older export', () => {
    const f = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
      properties: { ef_share: 0 },
    }
    const t = parseTrack(track(f))
    expect(t.segments[0].altM).toBe(0)
    expect(t.segments[0].efJ).toBe(0)
  })

  it('skips a degenerate single-point LineString', () => {
    const f = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0, 100]] },
      properties: { ef_tj: 5, ef_share: 0.1 },
    }
    expect(parseTrack(track(f)).segments).toHaveLength(0)
  })
})

describe('flightLevel', () => {
  it('converts metres to hundreds of feet', () => {
    expect(flightLevel(12215)).toBe(401)
    expect(flightLevel(0)).toBe(0)
  })
})
