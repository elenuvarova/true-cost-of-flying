import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { Flight, loadTrack, tonnes } from '../lib/data'
import { TrackData, parseTrack } from '../lib/track'
import { reduced } from '../lib/scroll'
import SegmentBars from './charts/SegmentBars'
import Appear from './Appear'

const FlightMap = lazy(() => import('./FlightMap'))

// Taylor Swift, 10 Dec 2024: 1 non-zero segment of 169 — the most extreme
// concentration in the set, and large enough (+12.1 t) not to be noise.
const HERO_FLIGHT = 'a81b13_20241210'

export default function OneSegment({ flights }: { flights: Flight[] }) {
  const stageRef = useRef<HTMLDivElement>(null)
  const [track, setTrack] = useState<TrackData | null>(null)
  const [active, setActive] = useState(0)

  const flight = flights.find((f) => f.flight_id === HERO_FLIGHT)

  useEffect(() => {
    let alive = true
    loadTrack(HERO_FLIGHT).then((gj) => {
      if (alive && gj) setTrack(parseTrack(gj))
    })
    return () => {
      alive = false
    }
  }, [])

  // Scroll through the section walks one cursor along the flight. Reduced
  // motion parks it on the peak segment instead of scrubbing.
  useEffect(() => {
    if (!track?.segments.length) return
    if (reduced()) {
      setActive(Math.max(0, track.peakIndex))
      return
    }
    const el = stageRef.current
    if (!el) return
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const span = Math.max(1, r.height - window.innerHeight)
        const p = Math.min(1, Math.max(0, -r.top / span))
        setActive(Math.round(p * (track.segments.length - 1)))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      cancelAnimationFrame(raf)
    }
  }, [track])

  if (!flight || !track) return null

  const peakT = Math.abs(flight.contrail_co2e_central) / 1000

  return (
    <section className="oneseg" id="one-segment">
      <div className="wrap">
        <Appear>
          <div className="eyebrow">03 — The concentration</div>
          <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
            One segment out of {track.segments.length}
          </h2>
          <p className="sec-sub">
            Contrail warming is not spread along a flight — it is made in the few minutes an aircraft spends inside
            ice-supersaturated air. On this Falcon 7X leg, {track.nonZero} of {track.segments.length} track segments
            produced any forcing at all, and it came to {tonnes(peakT * 1000)} t CO₂e. Across every flight here that
            formed a contrail, the median is 8 live segments out of about 156, and the top five carry 95% of the
            effect.
          </p>
        </Appear>
      </div>

      <div className="oneseg-stage" ref={stageRef}>
        <div className="oneseg-pin">
          {/* map and chart share one .wrap so they sit in exactly the same
              column — they are one instrument showing the same cursor twice. */}
          <div className="wrap">
            <div className="oneseg-map">
              <Suspense fallback={null}>
                <FlightMap
                  flightId={HERO_FLIGHT}
                  owner={flight.owner_label}
                  date={flight.date}
                  activeSegment={active}
                />
              </Suspense>
            </div>
            <SegmentBars segments={track.segments} active={active} peak={track.peakIndex} />
            <p className="oneseg-cap">
              Segment <b>{active + 1}</b> of {track.segments.length}
              {active === track.peakIndex && <b className="oneseg-hit"> — this is the one</b>}
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
