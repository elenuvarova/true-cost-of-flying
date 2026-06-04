import { Flight, Horizon, contrailKg, tonnes } from '../lib/data'
import { useCountUp } from '../lib/scroll'

export default function Reveal({ flight, horizon }: { flight: Flight; horizon: Horizon }) {
  const fuel = flight.fuel_co2_kg
  const contrail = contrailKg(flight, horizon)
  const combined = fuel + contrail
  const pct = fuel ? (100 * contrail) / fuel : 0
  const unstable = contrail > 0 && pct > 100
  const coolUnstable = contrail < 0 && Math.abs(pct) > 100

  const fuelC = useCountUp(fuel / 1000, 1300)
  const combC = useCountUp(combined / 1000, 1700, true)

  const c100 = flight.contrail_co2e_central
  const hr = horizon === 'GWP20' && c100 ? contrail / c100 : 1
  const band = [(fuel + flight.contrail_co2e_low * hr) / 1000, (fuel + flight.contrail_co2e_high * hr) / 1000].sort(
    (a, b) => a - b,
  )

  let combClass = ''
  let bar: React.ReactNode
  let delta: React.ReactNode
  if (contrail > 0 && pct >= 1) {
    const warmW = Math.max(6, (100 * contrail) / combined)
    combClass = 'warm'
    bar = (
      <div className="revbar">
        <span className="f" style={{ width: `${100 - warmW}%` }}>Fuel {tonnes(fuel, 0)} t</span>
        <span className="w" style={{ width: `${warmW}%` }}>+{tonnes(contrail)} t</span>
      </div>
    )
    delta = (
      <span className="delta">
        {unstable ? `+${tonnes(contrail)} t contrails — contrail-dominated` : `contrails add +${pct.toFixed(0)}%`}
      </span>
    )
  } else if (contrail < 0 && pct <= -1) {
    combClass = 'cool'
    bar = (
      <div className="revbar">
        <span className="f" style={{ width: '100%' }}>Fuel {tonnes(fuel, 0)} t — contrails net-cooled this flight</span>
      </div>
    )
    delta = (
      <span className="delta cool">
        contrails cooled by {tonnes(Math.abs(contrail))} t{coolUnstable ? '' : ` (${pct.toFixed(0)}%)`}
      </span>
    )
  } else {
    bar = (
      <div className="revbar">
        <span className="f" style={{ width: '100%' }}>Fuel {tonnes(fuel, 0)} t — no significant contrail formed</span>
      </div>
    )
    delta = <span className="delta flat">contrails: negligible (&lt;1%)</span>
  }

  return (
    <>
      <div className="reveal-grid">
        <div className="rev">
          <div className="l">Fuel CO₂ — what every tracker shows</div>
          <div className="big fuel" ref={fuelC.ref as any}>
            {fuelC.val.toFixed(1)} <small>t</small>
          </div>
        </div>
        <div className="rev">
          <div className="l">Combined CO₂e — fuel + contrails</div>
          <div className={`big ${combClass}`} ref={combC.ref as any}>
            {combC.val.toFixed(1)} <small>t CO₂e</small>
          </div>
          {delta}
        </div>
      </div>
      {bar}
      <div className="revcap">
        {horizon} · uncertainty band {band[0].toFixed(1)}–{band[1].toFixed(1)} t · contrail term carries ~70%
        uncertainty (IPCC “low confidence”). {flight.bizjet_alt_flag && 'Above CoCiP’s ~13 km cap → likely under-counted. '}
        {unstable &&
          'Contrails here exceed the flight’s own fuel CO₂, so we headline the absolute tonnes rather than a % — a per-flight percentage that large would invite confusion with the aviation-wide ~3× figure. '}
        {contrail < 0 &&
          'This flight’s contrails net-cooled — but CO₂ warms for centuries while contrail cooling is a one-off radiative event, so a net-negative figure does not mean the flight was climate-positive.'}
      </div>
      <span className="sr-only" role="status" aria-live="polite">
        Fuel {tonnes(fuel)} tonnes CO₂; combined {tonnes(combined)} tonnes CO₂e ({horizon}).
      </span>
    </>
  )
}
