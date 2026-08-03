import { NightGroup } from '../../lib/data'

const LABEL: Record<NightGroup['cls'], string> = { night: 'Night', mixed: 'Mixed', day: 'Day' }

// Warming right in crimson, cooling left in blue, from a centre zero axis.
export default function DivergingBar({ groups }: { groups: NightGroup[] }) {
  const max = Math.max(...groups.map((g) => Math.abs(g.co2eT)), 1)

  return (
    <div className="diverge">
      {groups.map((g) => {
        const pct = (Math.abs(g.co2eT) / max) * 50
        const warm = g.co2eT >= 0
        return (
          <div className="diverge-row" key={g.cls}>
            <div className="diverge-label">{LABEL[g.cls]}</div>
            <div className="diverge-track" aria-hidden="true">
              <span className="diverge-axis" />
              <i
                className={warm ? 'warm' : 'cool'}
                style={warm ? { left: '50%', width: `${pct}%` } : { right: '50%', width: `${pct}%` }}
              />
            </div>
            <div className={`diverge-val ${warm ? 'warm' : 'cool'}`}>
              {warm ? '+' : '−'}
              {Math.abs(g.co2eT).toFixed(1)} t
            </div>
            <div className="diverge-count">
              {g.warmed} warmed · {g.cooled} cooled
            </div>
          </div>
        )
      })}
      <p className="sr-only" data-testid="diverging-alt">
        {groups
          .map(
            (g) =>
              `${LABEL[g.cls]} flights: ${g.flights} formed a contrail, ${g.warmed} warmed, ${g.cooled} cooled, ` +
              `net ${g.co2eT >= 0 ? 'plus' : 'minus'} ${Math.abs(g.co2eT).toFixed(1)} tonnes CO₂e.`,
          )
          .join(' ')}
      </p>
    </div>
  )
}
