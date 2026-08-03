import { Segment } from '../../lib/track'

// A flight's per-segment |EF| as a sparse bar field. Almost every bar is zero;
// the point is how few carry the whole effect. Hand-written SVG so it inherits
// the palette and needs no chart library.
export default function SegmentBars({
  segments,
  active,
  peak,
}: {
  segments: Segment[]
  active: number
  peak: number
}) {
  if (!segments.length) return null

  const max = Math.max(...segments.map((s) => Math.abs(s.efJ)), 1)
  const nonZero = segments.filter((s) => s.efJ !== 0).length
  const w = 1000
  const h = 220
  const gap = 1
  const bw = Math.max(1, w / segments.length - gap)
  // The viewBox is ~1.4x taller than the rendered height, so a 1-unit stub
  // draws sub-pixel and the zero segments vanish. They must stay visible: the
  // whole claim is "N of 169", and you cannot see the 169 if they are invisible.
  const ZERO_H = 5
  const MIN_LIVE_H = 8

  return (
    <div className="segbars">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="presentation" aria-hidden="true">
        <line x1="0" y1={h - 1} x2={w} y2={h - 1} stroke="var(--hair)" strokeWidth="1" />
        {segments.map((s) => {
          const bh =
            s.efJ === 0 ? ZERO_H : Math.max((Math.abs(s.efJ) / max) * (h - 16), MIN_LIVE_H)
          const isPeak = s.index === peak
          const isActive = s.index === active && !isPeak
          const fill = s.efJ < 0 ? 'var(--cool)' : isPeak ? 'var(--warm-deep)' : 'var(--fuel)'
          return (
            <rect
              key={s.index}
              data-testid={isPeak ? 'seg-bar-peak' : isActive ? 'seg-bar-active' : 'seg-bar'}
              x={s.index * (bw + gap)}
              y={h - 1 - bh}
              width={bw}
              height={bh}
              fill={s.efJ === 0 ? 'var(--faint)' : fill}
              opacity={s.efJ === 0 ? (isActive ? 0.9 : 0.55) : isPeak || isActive ? 1 : 0.8}
            />
          )
        })}
      </svg>
      <p className="sr-only" data-testid="seg-bars-alt">
        Bar chart of contrail energy forcing for each of the {segments.length} track segments. {nonZero} of{' '}
        {segments.length} segments produced any forcing at all; the rest are zero.
      </p>
    </div>
  )
}
