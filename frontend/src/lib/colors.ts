// The brand tonal ramp — the warming-stripe spine of the whole site.
// blue (contrail COOLS) ← amber (fuel-CO₂ baseline / ~neutral) → red (contrail WARMS).
export type RGB = [number, number, number]

export const BG: RGB = [10, 20, 34]
export const AMBER: RGB = [232, 178, 74] // fuel CO₂ / neutral (gold)
export const RED: RGB = [214, 38, 60] // contrail warming (crimson)
export const BLUE: RGB = [90, 160, 224] // contrail cooling

export const lerp = (a: RGB, b: RGB, t: number): RGB => [
  Math.round(a[0] + (b[0] - a[0]) * t),
  Math.round(a[1] + (b[1] - a[1]) * t),
  Math.round(a[2] + (b[2] - a[2]) * t),
]

// ef_share = a segment's share of the flight's total energy forcing.
// Most segments ~0 (amber); the ice-supersaturated bursts spike positive (red).
export function efColor(s: number, scale = 0.06): RGB {
  if (s > 0.012) return lerp(AMBER, RED, Math.min(1, s / scale))
  if (s < -0.012) return lerp(AMBER, BLUE, Math.min(1, -s / scale))
  return AMBER
}

export const rgbCss = (c: RGB, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`
