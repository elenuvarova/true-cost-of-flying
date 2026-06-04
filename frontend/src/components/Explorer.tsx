import { useMemo, useState } from 'react'
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
import FlightMap from './FlightMap'
import Appear from './Appear'

const W = 100

function ownerStats(fs: Flight[], h: Horizon) {
  const fuelKg = fs.reduce((s, f) => s + f.fuel_co2_kg, 0)
  const contrailKgSum = fs.reduce((s, f) => s + contrailKg(f, h), 0)
  return {
    fuelT: fuelKg / 1000,
    contrailT: contrailKgSum / 1000,
    warm: fs.filter((f) => f.contrail_co2e_central > W).length,
    cool: fs.filter((f) => f.contrail_co2e_central < -W).length,
    zero: fs.filter((f) => Math.abs(f.contrail_co2e_central) <= W).length,
  }
}

function flightLabel(f: Flight, h: Horizon) {
  const c = contrailKg(f, h)
  const tag = c > W ? `+${tonnes(c)} t 🔥` : c < -W ? `−${tonnes(Math.abs(c))} t ❄` : '~0'
  const d = new Date(f.date + 'T00:00:00')
  const ds = isNaN(+d) ? f.date : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  return `${ds} · ${tonnes(f.fuel_co2_kg + c, 0)} t · ${tag}`
}

export default function Explorer({ flights, horizon }: { flights: Flight[]; horizon: Horizon }) {
  const owners = useMemo(() => Array.from(new Set(flights.map((f) => f.owner_label))), [flights])
  const ordered = useMemo(() => {
    const sum = (o: string) =>
      flights.filter((f) => f.owner_label === o).reduce((s, f) => s + f.fuel_co2_kg + contrailKg(f, horizon), 0)
    const others = owners.filter((o) => !FEATURED_ORDER.includes(o)).sort((a, b) => sum(b) - sum(a))
    return [...FEATURED_ORDER.filter((o) => owners.includes(o)), ...others]
  }, [owners, flights, horizon])

  const [owner, setOwner] = useState('Donald Trump')
  const [fid, setFid] = useState<string | undefined>(undefined)

  const myFlights = useMemo(() => flightsFor(flights, owner, horizon), [flights, owner, horizon])
  if (!flights.length || !myFlights.length) return <section className="exp wrap" id="explore" />

  const standout = standoutFlight(myFlights)
  const sel = myFlights.find((f) => f.flight_id === fid) ?? standout
  const portrait = PORTRAITS[owner]
  const st = ownerStats(myFlights, horizon)
  const ct = st.contrailT
  const cClass = ct > 0.1 ? 'warm' : ct < -0.1 ? 'cool' : ''
  const cStr = ct > 0.1 ? `+${tonnes(ct * 1000)}` : ct < -0.1 ? `−${tonnes(Math.abs(ct) * 1000)}` : '~0'
  const wcTotal = Math.max(1, st.warm + st.cool + st.zero)

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
      </Appear>

      <div className="pills">
        {ordered.map((o) => (
          <button
            key={o}
            className={`pill ${o === owner ? 'on' : ''}`}
            onClick={() => {
              setOwner(o)
              setFid(undefined)
            }}
          >
            {FEATURED_ORDER.includes(o) && <span className="star">★</span>}
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
            <div className="v fuel">
              {tonnes(st.fuelT * 1000)} <span style={{ fontSize: '.5em', color: 'var(--muted)' }}>t</span>
            </div>
          </div>
          <div className="fstat">
            <div className="l">Contrails net · {horizon}</div>
            <div className={`v ${cClass}`}>
              {cStr} <span style={{ fontSize: '.5em', color: 'var(--muted)' }}>t</span>
            </div>
          </div>
          <div className="fstat">
            <div className="l">Outcome · {myFlights.length} flights</div>
            <div className="wcbar">
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
          <label>Pick one of {short(owner)}’s {myFlights.length} flights — defaulting to the most telling:</label>
          <div className="fp">
            {myFlights.map((f) => (
              <button key={f.flight_id} className={f.flight_id === sel.flight_id ? 'on' : ''} onClick={() => setFid(f.flight_id)}>
                {flightLabel(f, horizon)}
              </button>
            ))}
          </div>
        </div>

        <Reveal flight={sel} horizon={horizon} />

        <div className="exp-map">
          <FlightMap flightId={sel.flight_id} />
        </div>
      </div>
    </section>
  )
}
