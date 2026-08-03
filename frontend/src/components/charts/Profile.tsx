import { useState } from 'react'
import { TrackData, flightLevel } from '../../lib/track'

type Tab = 'alt' | 'ef'

// Altitude and contrail-forcing profiles for one flight, sharing the map's
// cursor. The range input is the accessible control; the SVG is decoration.
export default function Profile({
  track,
  active,
  onActive,
}: {
  track: TrackData
  active: number
  onActive: (i: number) => void
}) {
  const [tab, setTab] = useState<Tab>('alt')
  const segs = track.segments
  if (!segs.length) return null

  const w = 1000
  const h = 150
  const last = segs.length - 1
  const maxAlt = Math.max(track.maxAltM, 1)
  const maxEf = Math.max(...segs.map((s) => Math.abs(s.efJ)), 1)

  const x = (i: number) => (i / Math.max(1, last)) * w
  const y = (s: { altM: number; efJ: number }) =>
    tab === 'alt' ? h - (s.altM / maxAlt) * (h - 8) : h - (Math.abs(s.efJ) / maxEf) * (h - 8)

  const d = segs.map((s, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(s).toFixed(1)}`).join(' ')
  const idx = Math.min(last, Math.max(0, active))
  const cur = segs[idx]

  return (
    <div className="profile">
      <div className="profile-head">
        <div className="hztoggle" role="group" aria-label="Profile metric">
          <button className={tab === 'alt' ? 'on' : ''} aria-pressed={tab === 'alt'} onClick={() => setTab('alt')}>
            Altitude
          </button>
          <button className={tab === 'ef' ? 'on' : ''} aria-pressed={tab === 'ef'} onClick={() => setTab('ef')}>
            Contrail EF
          </button>
        </div>
        <div className="profile-read" data-testid="profile-alt">
          FL{flightLevel(cur.altM)} · segment {cur.index + 1} of {segs.length} ·{' '}
          {tab === 'alt' ? 'altitude' : 'contrail forcing'}
        </div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="presentation" aria-hidden="true">
        <path
          d={d}
          fill="none"
          stroke={tab === 'alt' ? 'var(--cool)' : 'var(--warm)'}
          strokeWidth="2.5"
          vectorEffect="non-scaling-stroke"
        />
        <line
          x1={x(idx)}
          y1="0"
          x2={x(idx)}
          y2={h}
          stroke="var(--ink-2)"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
          opacity=".7"
        />
        <circle cx={x(idx)} cy={y(cur)} r="4" fill="var(--ink)" />
      </svg>

      <label className="sr-only" htmlFor="profile-scrub">
        Scrub along the flight path
      </label>
      <input
        id="profile-scrub"
        className="profile-scrub"
        type="range"
        min={0}
        max={last}
        step={1}
        value={idx}
        aria-valuemin={0}
        aria-valuemax={last}
        aria-valuenow={cur.index}
        aria-valuetext={`Segment ${cur.index + 1} of ${segs.length}, flight level ${flightLevel(cur.altM)}`}
        onChange={(e) => onActive(Number(e.target.value))}
      />
    </div>
  )
}
