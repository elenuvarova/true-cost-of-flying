import { Suspense, lazy, useMemo, useState } from 'react'
import {
  Flight,
  Horizon,
  FEATURED_ORDER,
  PORTRAITS,
  contrailKg,
  flightsFor,
  short,
  standoutFlight,
  tonnes,
} from '../lib/data'
import { rgbCss, AMBER, RED, BLUE } from '../lib/colors'
import Reveal from './Reveal'
import Appear from './Appear'

// Code-split the heavy deck.gl/maplibre map off the hero's critical path.
const FlightMap = lazy(() => import('./FlightMap'))

const W = 100

function ownerStats(fs: Flight[], h: Horizon) {
  const fuelKg = fs.reduce((s, f) => s + f.fuel_co2_kg, 0)
  const contrailKgSum = fs.reduce((s, f) => s + contrailKg(f, h), 0)
  return {
    fuelT: fuelKg / 1000,
    contrailT: contrailKgSum / 1000,
    warm: fs.filter((f) => contrailKg(f, h) > W).length,
    cool: fs.filter((f) => contrailKg(f, h) < -W).length,
    zero: fs.filter((f) => Math.abs(contrailKg(f, h)) <= W).length,
  }
}

function prettyDate(d: string) {
  const dt = new Date(d + 'T00:00:00')
  return isNaN(+dt) ? d : dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function flightLabel(f: Flight, h: Horizon) {
  const c = contrailKg(f, h)
  const tag = c > W ? `warms +${tonnes(c)} t` : c < -W ? `cools −${tonnes(Math.abs(c))} t` : 'contrails ~0'
  return `${prettyDate(f.date)} · ${tonnes(f.fuel_co2_kg + c, 0)} t CO₂e · ${tag}`
}

export default function Explorer({
  flights,
  horizon,
  onHorizon,
}: {
  flights: Flight[]
  horizon: Horizon
  onHorizon: (h: Horizon) => void
}) {
  const owners = useMemo(() => Array.from(new Set(flights.map((f) => f.owner_label))), [flights])
  const ordered = useMemo(() => {
    const sum = (o: string) =>
      flights.filter((f) => f.owner_label === o).reduce((s, f) => s + f.fuel_co2_kg + contrailKg(f, horizon), 0)
    const others = owners.filter((o) => !FEATURED_ORDER.includes(o)).sort((a, b) => sum(b) - sum(a))
    return [...FEATURED_ORDER.filter((o) => owners.includes(o)), ...others]
  }, [owners, flights, horizon])

  const [ownerSel, setOwner] = useState('')
  const [fid, setFid] = useState<string | undefined>(undefined)

  if (!flights.length || !ordered.length) return <section className="exp wrap" id="explore" />
  const owner = ownerSel && owners.includes(ownerSel) ? ownerSel : ordered[0]

  const myFlights = flightsFor(flights, owner, horizon)
  const standout = standoutFlight(myFlights)
  const sel = myFlights.find((f) => f.flight_id === fid) ?? standout
  const portrait = PORTRAITS[owner]
  const st = ownerStats(myFlights, horizon)
  const ct = st.contrailT
  const cClass = ct > 0.1 ? 'warm' : ct < -0.1 ? 'cool' : ''
  const cStr = ct > 0.1 ? `+${tonnes(ct * 1000)}` : ct < -0.1 ? `−${tonnes(Math.abs(ct) * 1000)}` : '~0'

  return (
    <section className="exp wrap" id="explore">
      <Appear>
        <div className="eyebrow">02 — The explorer</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Pick a flyer, then the{' '}
          <span style={{ fontFamily: 'var(--serif)', fontStyle: 'italic', fontWeight: 600, color: 'var(--warm)' }}>
            same flight, two numbers
          </span>
        </h2>
        <p className="sec-sub">
          Fuel is the certain harm. Contrails are the wildcard — a concentrated effect from crossing ice-supersaturated
          air, not a flat multiplier. Usually near zero, occasionally a lot.
        </p>
        <div className="hzrow">
          <div className="hztoggle" role="group" aria-label="Time horizon">
            {(['GWP100', 'GWP20'] as Horizon[]).map((h) => (
              <button key={h} className={h === horizon ? 'on' : ''} aria-pressed={h === horizon} onClick={() => onHorizon(h)}>
                {h}
              </button>
            ))}
          </div>
          <span className="hz-note">
            GWP20 weights short-lived contrails heavier than the 100-year basis — watch the contrail number move. (A
            time-horizon choice, not the aviation-wide ~3× ERF.)
          </span>
        </div>
      </Appear>

      <div className="pills">
        {ordered.map((o) => (
          <button
            key={o}
            className={`pill ${o === owner ? 'on' : ''}`}
            aria-pressed={o === owner}
            onClick={() => { setOwner(o); setFid(undefined) }}
          >
            {FEATURED_ORDER.includes(o) && <span className="star" aria-hidden="true">★</span>}
            {short(o)}
          </button>
        ))}
      </div>
      <p className="pills-note">★ have full verified write-ups; the others show stats computed straight from the data.</p>

      <div className="flyer">
        <div className="flyer-head">
          <div>
            <div className="flyer-name">{owner}</div>
            <div className="flyer-ac">{portrait?.ac ?? `${myFlights[0].ac_type} · ${myFlights.length} flights`}</div>
          </div>
          {portrait && <div className="flyer-badge">{portrait.badge}</div>}
        </div>

        <div className="flyer-stats">
          <div className="fstat">
            <div className="l">Fuel CO₂ · {myFlights.length} flights</div>
            <div className="v fuel">{tonnes(st.fuelT * 1000)} <span style={{ fontSize: '.5em', color: 'var(--muted)' }}>t</span></div>
          </div>
          <div className="fstat">
            <div className="l">Contrails net · {horizon}</div>
            <div className={`v ${cClass}`}>{cStr} <span style={{ fontSize: '.5em', color: 'var(--muted)' }}>t</span></div>
          </div>
          <div className="fstat">
            <div className="l">Outcome · {myFlights.length} flights</div>
            <div className="wcbar" aria-hidden="true">
              {st.warm > 0 && <i style={{ flex: st.warm, background: rgbCss(RED) }} />}
              {st.cool > 0 && <i style={{ flex: st.cool, background: rgbCss(BLUE) }} />}
              {st.zero > 0 && <i style={{ flex: st.zero, background: '#33455c' }} />}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: '.72rem', marginTop: '.35rem' }}>
              {st.warm} warmed · {st.cool} cooled · {st.zero} ~none
            </div>
          </div>
        </div>

        {portrait ? (
          <div className="flyer-line">{portrait.headline}</div>
        ) : (
          <div className="flyer-line">
            {myFlights[0].ac_type} · {myFlights.length} tracked flights. Fuel is the certain number (
            <b>{tonnes(st.fuelT * 1000)} t CO₂</b>); contrails netted <b>{cStr} t</b> ({horizon}) across the sample —{' '}
            {st.warm} warmed, {st.cool} cooled, {st.zero} formed essentially none.
          </div>
        )}

        <div className="flight-pick">
          <label>
            Pick one of {short(owner)}’s {myFlights.length} flights <span className="fp-key">(date · combined CO₂e · contrails)</span> — defaulting to the most telling:
          </label>
          <div className="fp">
            {myFlights.map((f) => (
              <button key={f.flight_id} className={f.flight_id === sel.flight_id ? 'on' : ''} aria-pressed={f.flight_id === sel.flight_id} onClick={() => setFid(f.flight_id)}>
                {flightLabel(f, horizon)}
              </button>
            ))}
          </div>
        </div>

        <Reveal flight={sel} horizon={horizon} />

        <div className="exp-map">
          <Suspense fallback={null}>
            <FlightMap flightId={sel.flight_id} owner={owner} date={prettyDate(sel.date)} />
          </Suspense>
          <div className="map-cap">
            <b>{owner} · {prettyDate(sel.date)}</b> — the contrail inks itself along the real flight path, coloured by where warming happened.
            <div className="legend">
              <span><i style={{ background: rgbCss(RED) }} /> contrail warms</span>
              <span><i style={{ background: rgbCss(AMBER) }} /> fuel-CO₂ baseline</span>
              <span><i style={{ background: rgbCss(BLUE) }} /> contrail cools</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
