import { useEffect, useState } from 'react'
import { Comparator, loadComparators, tonnes } from '../lib/data'
import Appear from './Appear'

export default function NightWidebodies() {
  const [rows, setRows] = useState<Comparator[] | null>(null)

  useEffect(() => {
    let alive = true
    loadComparators().then((r) => alive && setRows(r))
    return () => {
      alive = false
    }
  }, [])

  if (!rows || !rows.length) return null

  const fuel = rows.reduce((s, r) => s + r.fuel_co2_kg, 0)
  const contrail = rows.reduce((s, r) => s + r.contrail_co2e_central, 0)
  const aggregate = fuel ? (100 * contrail) / fuel : 0
  const maxPct = Math.max(...rows.map((r) => r.contrail_pct_of_fuel), 1)

  return (
    <section className="cmp wrap" id="night-widebodies">
      <Appear>
        <div className="eyebrow">05 — The other end of the scale</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Five night transatlantic widebodies
        </h2>
        <p className="sec-sub">
          Same pipeline, same physics, different regime: {rows.length} scheduled widebodies crossing the North Atlantic
          at night. Where the daytime private jets netted close to zero, these did not.
        </p>
      </Appear>

      <div className="cmp-list">
        {rows.map((r) => (
          <div className="cmp-row" data-testid="cmp-row" key={r.flight_id}>
            <div className="cmp-name">
              <b>{r.owner_label}</b>
              <span>{r.ac_type}</span>
            </div>
            <div className="cmp-bar" aria-hidden="true">
              <i style={{ width: `${Math.max(2, (r.contrail_pct_of_fuel / maxPct) * 100)}%` }} />
            </div>
            <div className="cmp-nums">
              <span className="fuel">{tonnes(r.fuel_co2_kg, 0)} t fuel</span>
              <span className="warm">+{tonnes(r.contrail_co2e_central, 0)} t contrails</span>
              <b>{r.contrail_pct_of_fuel.toFixed(0)}%</b>
            </div>
          </div>
        ))}
      </div>

      <p className="cmp-agg" data-testid="cmp-aggregate">
        Across all {rows.length}, contrail warming came to <b>{aggregate.toFixed(0)}%</b> of their fuel CO₂ — against
        roughly zero for the daytime private jets above. Same code, same ERA5, same CoCiP. The difference is regime:
        night, and crossing ice-supersaturated air.
      </p>
      <p className="cmp-caveat" data-testid="cmp-caveat">
        This is a contrail-to-fuel ratio for these five specific flights, <b>not a per-flight multiplier</b> and not
        the aviation-wide figure. One of the five crossed no ice-supersaturated air at all and came in near zero, which
        is the point: the effect is a lottery of where and when you fly, not a constant.
      </p>
    </section>
  )
}
