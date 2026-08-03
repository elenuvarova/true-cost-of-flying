import { useState } from 'react'
import {
  Horizon,
  METRIC_LABEL,
  Metric,
  OwnerAgg,
  metricT,
  rankByMetric,
  reshuffleStats,
  tonnes,
} from '../lib/data'
import { reduced } from '../lib/scroll'
import Motion, { m } from '../lib/motion'
import HorizonToggle from './HorizonToggle'
import Appear from './Appear'

const METRICS: Metric[] = ['fuel', 'combined', 'contrail']

// 1st, 2nd, 3rd, 4th … 11th, 12th, 13th. The caption says these out loud, so
// the teens exceptions matter.
function ordinal(n: number): string {
  const rem100 = n % 100
  if (rem100 >= 11 && rem100 <= 13) return `${n}th`
  const rem10 = n % 10
  return `${n}${rem10 === 1 ? 'st' : rem10 === 2 ? 'nd' : rem10 === 3 ? 'rd' : 'th'}`
}

const stripeColor = (t: OwnerAgg['tier']) =>
  t === 'high' ? 'var(--warm-deep)' : t === 'med' ? 'var(--fuel)' : 'var(--cool)'

function Chips({ o }: { o: OwnerAgg }) {
  return (
    <div className="chips">
      <span className={`tier ${o.tier}`}>{o.tier === 'high' ? 'High' : o.tier === 'med' ? 'Med' : 'Low'}</span>
      {o.proxy && <span className="chip">⚠ proxy type</span>}
      {o.bizjet && <span className="chip">⚠ above cap · under-counted</span>}
    </div>
  )
}

// Signed magnitude bar. Cooling owners get a blue bar, so "contrails only"
// never renders a negative as a stubby positive.
function Mag({ value, max, cool }: { value: number; max: number; cool: boolean }) {
  const pct = max > 0 ? Math.max(2, (Math.abs(value) / max) * 100) : 2
  return (
    <div className="mag">
      <i
        style={{
          width: `${pct}%`,
          background: cool
            ? 'linear-gradient(90deg,var(--cool),#2f6aa8)'
            : 'linear-gradient(90deg,var(--fuel),var(--warm) 78%,var(--warm-deep))',
        }}
      />
    </div>
  )
}

function Row({ o, rank, metric, max }: { o: OwnerAgg; rank: number; metric: Metric; max: number }) {
  const v = metricT(o, metric)
  const hero = rank === 1
  const unit = metric === 'contrail' ? 't CO₂e contrails' : hero ? 't CO₂e' : 't'
  const sign = metric === 'contrail' && v > 0 ? '+' : metric === 'contrail' && v < 0 ? '−' : ''
  return (
    <m.div
      layout={!reduced()}
      transition={{ type: 'spring', stiffness: 260, damping: 30 }}
      className={`lb-card ${hero ? 'lb-hero' : 'lb-row'}`}
    >
      <span className="stripe" style={{ background: stripeColor(o.tier) }} />
      <div className="lb-top">
        <div>
          <div className="lb-rank">Rank {String(rank).padStart(2, '0')}</div>
          <div className="lb-name" data-testid="lb-name">
            {o.owner}
          </div>
          <div className="lb-ac">
            {o.ac_type} · {o.flights} flights
            {hero && ` · ${o.warm} warmed · ${o.cool} cooled · ${o.zero} ~none`}
          </div>
        </div>
        <div className="lb-val" style={{ textAlign: 'right' }}>
          <div className="t">
            {sign}
            {tonnes(Math.abs(v) * 1000)} <span className="u">{unit}</span>
          </div>
        </div>
      </div>
      <Mag value={v} max={max} cool={v < 0} />
      <Chips o={o} />
    </m.div>
  )
}

export default function Leaderboard({
  owners,
  total,
  horizon,
  onHorizon,
}: {
  owners: OwnerAgg[]
  total: number
  horizon: Horizon
  onHorizon: (h: Horizon) => void
}) {
  const [metric, setMetric] = useState<Metric>('combined')
  if (!owners.length) return null

  const ranked = rankByMetric(owners, metric)
  const max = Math.max(...ranked.map((o) => Math.abs(metricT(o, metric))))
  // The caption always describes the fuel -> combined move, whichever metric is
  // on screen: that move is the claim, the tabs are how you check it.
  const shuffle = reshuffleStats(owners, 'fuel', 'combined')

  return (
    <section className="lb wrap" id="leaderboard">
      <Appear>
        <div className="eyebrow">01 — The ranking</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Who warmed the most
        </h2>
        <p className="sec-sub">
          {total} tracked flights across {owners.length} public-figure jets. Switch the metric and watch the order
          change — that change is the whole point.
        </p>
        <HorizonToggle
          horizon={horizon}
          onHorizon={onHorizon}
          note="GWP20 weights short-lived contrails heavier than the 100-year basis. (A time-horizon choice, not the aviation-wide ~3× ERF.)"
        />
      </Appear>

      <div className="metricrow">
        <div className="hztoggle" role="group" aria-label="Ranking metric">
          {METRICS.map((mm) => (
            <button key={mm} className={mm === metric ? 'on' : ''} aria-pressed={mm === metric} onClick={() => setMetric(mm)}>
              {METRIC_LABEL[mm]}
            </button>
          ))}
        </div>
        <p className="hz-note" data-testid="reshuffle-note">
          {shuffle.biggest ? (
            <>
              Counting contrails moves{' '}
              <b>
                {shuffle.moved} of {shuffle.total}
              </b>{' '}
              — {shuffle.biggest.owner} goes from {ordinal(shuffle.biggest.from)} to {ordinal(shuffle.biggest.to)} at{' '}
              {horizon}.
            </>
          ) : (
            <>At {horizon}, counting contrails leaves the order unchanged.</>
          )}
        </p>
      </div>

      <Motion>
        <div className="lb-grid">
          {ranked.map((o, i) => (
            <Row key={o.owner} o={o} rank={i + 1} metric={metric} max={max} />
          ))}
        </div>
      </Motion>

      <span className="sr-only" role="status" aria-live="polite" data-testid="lb-live">
        Ranked by {METRIC_LABEL[metric]}: {ranked.map((o, i) => `${i + 1}. ${o.owner}`).join(', ')}.
      </span>
    </section>
  )
}
