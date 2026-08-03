import { Flight, Horizon, contrailKg, tonnes } from '../lib/data'
import Appear from './Appear'

export default function HowWeKnow({ flights, horizon }: { flights: Flight[]; horizon: Horizon }) {
  const n = flights.length
  const formed = flights.filter((f) => f.contrail_ef_joules !== 0).length
  const flagged = flights.filter((f) => f.bizjet_alt_flag || f.proxy_type_flag || f.coverage_gap_flag).length

  const contrail = flights.reduce((s, f) => s + contrailKg(f, horizon), 0)
  // Scale the GWP100 low/high endpoints to the chosen horizon, then sort —
  // a negative central would otherwise put "high" below "low".
  const scale = (v: number, f: Flight) => {
    const c100 = f.contrail_co2e_central
    return c100 ? v * (contrailKg(f, horizon) / c100) : v
  }
  const low = flights.reduce((s, f) => s + scale(f.contrail_co2e_low, f), 0)
  const high = flights.reduce((s, f) => s + scale(f.contrail_co2e_high, f), 0)
  const band = [low, high].sort((a, b) => a - b)
  const width = Math.max(1e-6, band[1] - band[0])
  const centrePct = Math.min(100, Math.max(0, ((contrail - band[0]) / width) * 100))

  return (
    <section className="hwk wrap" id="how-we-know">
      <Appear>
        <div className="eyebrow">06 — The honesty section</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          How we know this, and what we don’t
        </h2>
      </Appear>

      <div className="hwk-grid">
        <div className="hwk-card">
          <div className="hwk-l">Contrail incidence</div>
          <div className="hwk-v" data-testid="hwk-incidence">
            {formed} of {n}
          </div>
          <p>
            flights formed a contrail with any measurable forcing — {Math.round((100 * formed) / Math.max(1, n))}%.
            Teoh et al. (2024) find roughly 24% across a whole fleet; ours runs higher because the sample was
            deliberately weighted towards night.
          </p>
        </div>

        <div className="hwk-card">
          <div className="hwk-l">Flagged for caution</div>
          <div className="hwk-v" data-testid="hwk-flagged">
            {flagged} of {n}
          </div>
          <p>
            flights carry at least one caveat: cruising above CoCiP’s ~13 km ceiling (so under-counted), flown on a
            proxy aircraft type, or with a gap in ADS-B coverage. Each is labelled where it appears.
          </p>
        </div>

        <div className="hwk-card hwk-wide">
          <div className="hwk-l">Uncertainty · {horizon}</div>
          <div className="hwk-band" aria-hidden="true">
            <i />
            <span style={{ left: `${centrePct}%` }} />
          </div>
          <div className="hwk-bandnums" data-testid="hwk-band">
            <span>{tonnes(band[0])} t</span>
            <b>{tonnes(contrail)} t central</b>
            <span>{tonnes(band[1])} t</span>
          </div>
          <p>
            The contrail term carries roughly ±70% uncertainty — the IPCC rates confidence in contrail radiative
            forcing as <i>low</i>. Every contrail figure on this page sits inside that band. Fuel CO₂, by contrast, is
            near-certain: it follows from fuel burnt.
          </p>
        </div>

        <div className="hwk-card">
          <div className="hwk-l">The EF → CO₂e bridge</div>
          <div className="hwk-v">0.8%</div>
          <p>
            is how far our energy-forcing-to-CO₂e conversion sits from the factor Contrails.org publishes. We then
            apply a 0.42 efficacy factor on top, making these figures more conservative than a raw radiative-forcing
            basis would be.
          </p>
        </div>

        <div className="hwk-card" data-testid="hwk-bias">
          <div className="hwk-l">Selection bias</div>
          <div className="hwk-v">Night-weighted</div>
          <p>
            Part of this dataset was <b>deliberately harvested</b> for night flights, because that is where the
            physics is most visible. The direction of the day/night result holds; the <i>share</i> of flights forming
            contrails here is an upper estimate, not an unbiased sample of aviation.
          </p>
        </div>

        <div className="hwk-card hwk-wide" data-testid="hwk-excluded">
          <div className="hwk-l">What is not counted</div>
          <p>
            These totals are <b>fuel CO₂ plus contrails only</b>. They omit NOx, water vapour and aerosols. That is
            why this is <b>not the aviation-wide ~3× figure</b> you may have read: that number covers every
            non-CO₂ term across the whole fleet, and adding it here would double-count the contrail effect we already
            compute directly. Aircraft, not people.
          </p>
        </div>
      </div>
    </section>
  )
}
