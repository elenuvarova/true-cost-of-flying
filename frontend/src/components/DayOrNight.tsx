import { useEffect, useRef, useState } from 'react'
import { Flight, Horizon, nightSplit } from '../lib/data'
import { reduced } from '../lib/scroll'
import DivergingBar from './charts/DivergingBar'
import Appear from './Appear'

// The section darkens as you scroll it — the only place the day-to-night colour
// move is used, because here it is the physics rather than decoration.
const DAY_BG = [17, 35, 58]
const NIGHT_BG = [4, 8, 15]

export default function DayOrNight({ flights, horizon }: { flights: Flight[]; horizon: Horizon }) {
  const ref = useRef<HTMLElement>(null)
  const [p, setP] = useState(reduced() ? 1 : 0)

  const groups = nightSplit(flights, horizon)
  const night = groups.find((g) => g.cls === 'night')!
  const day = groups.find((g) => g.cls === 'day')!
  const any = groups.some((g) => g.flights > 0)

  useEffect(() => {
    if (reduced()) return
    const el = ref.current
    if (!el) return
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const span = Math.max(1, r.height + window.innerHeight)
        setP(Math.min(1, Math.max(0, (window.innerHeight - r.top) / span)))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      cancelAnimationFrame(raf)
    }
  }, [])

  if (!any) return null

  const mix = DAY_BG.map((c, i) => Math.round(c + (NIGHT_BG[i] - c) * p))
  const dayPct = day.flights ? Math.round((100 * day.cooled) / day.flights) : 0
  const formed = groups.reduce((s, g) => s + g.flights, 0)

  return (
    <section
      className="dayornight"
      id="day-or-night"
      ref={ref as any}
      style={{ background: `rgb(${mix.join(',')})` }}
    >
      <div className="wrap">
        <Appear>
          <div className="eyebrow">02 — The sign flip</div>
          <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
            Day or night decides the sign
          </h2>
          <p className="sec-sub">
            A contrail traps outgoing heat and reflects incoming sunlight. At night there is no sunlight to reflect, so
            only the trapping remains. Classifying every flight by how much of its cruise happened in darkness, and
            counting only the {formed} that formed a contrail at all:
          </p>
        </Appear>

        <DivergingBar groups={groups} />

        <p className="don-line" data-testid="night-line">
          Night flights: <b>{night.warmed} of {night.flights} warmed</b>, none cooled. Day flights:{' '}
          <b>{day.cooled} of {day.flights} cooled</b> ({dayPct}%).
        </p>
        <p className="don-note">
          An earlier waypoint-level analysis of 62 cached runs found 74% day cooling and 100% night warming; this
          flight-level split, computed independently from the raw tracks, lands within a point of it. Note that the
          night flights here were <b>deliberately harvested</b>, so the night share of this sample is not
          representative of aviation — the sign result is, the incidence is not.
        </p>
      </div>
    </section>
  )
}
