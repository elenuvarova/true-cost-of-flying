// Parse an exported track geojson into typed segments.
//
// One parser for both the "one segment" bar chart and the explorer's altitude
// profile, so a segment index means exactly the same thing in the chart, on the
// map and in the scrubber.

export interface Segment {
  index: number
  efJ: number // signed energy forcing, joules (+ warms, − cools)
  efShare: number // share of the flight's total forcing, as exported
  lon: number // segment midpoint
  lat: number
  altM: number // mean altitude across the segment, metres
}

export interface TrackData {
  segments: Segment[]
  totalAbsEfJ: number
  peakIndex: number // index of the largest |efJ|, or -1 when nothing formed
  nonZero: number
  maxAltM: number
}

const EMPTY: TrackData = { segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 }

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

export function parseTrack(gj: unknown): TrackData {
  const features = (gj as any)?.features
  if (!Array.isArray(features)) return { ...EMPTY }

  const segments: Segment[] = []
  let totalAbsEfJ = 0
  let peakIndex = -1
  let peakAbs = 0
  let nonZero = 0
  let maxAltM = 0

  for (const f of features) {
    const g = f?.geometry
    const coords = g?.coordinates
    if (g?.type !== 'LineString' || !Array.isArray(coords) || coords.length < 2) continue

    const a = coords[0]
    const b = coords[coords.length - 1]
    // ef_tj is terajoules in the export; the science talks in joules.
    const efJ = num(f?.properties?.ef_tj) * 1e12
    const alts = coords.map((c: number[]) => num(c[2]))
    const altM = Math.round(alts.reduce((s: number, v: number) => s + v, 0) / alts.length)

    const index = segments.length
    segments.push({
      index,
      efJ,
      efShare: num(f?.properties?.ef_share),
      lon: (num(a[0]) + num(b[0])) / 2,
      lat: (num(a[1]) + num(b[1])) / 2,
      altM,
    })

    const abs = Math.abs(efJ)
    totalAbsEfJ += abs
    if (abs > 0) nonZero++
    if (abs > peakAbs) {
      peakAbs = abs
      peakIndex = index
    }
    maxAltM = Math.max(maxAltM, ...alts)
  }

  return { segments, totalAbsEfJ, peakIndex, nonZero, maxAltM }
}

// Flight level = altitude in hundreds of feet. FL401 ≈ 12 215 m.
export const flightLevel = (altM: number): number => Math.round((altM * 3.28084) / 100)
