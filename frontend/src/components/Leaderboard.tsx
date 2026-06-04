import { OwnerAgg, tonnes } from '../lib/data'
import Appear from './Appear'

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

function Mag({ pct }: { pct: number }) {
  return (
    <div className="mag">
      <i style={{ width: `${Math.max(2, pct)}%` }} />
    </div>
  )
}

export default function Leaderboard({ owners, total }: { owners: OwnerAgg[]; total: number }) {
  if (!owners.length) return null
  const max = owners[0].combinedT
  const [first, ...rest] = owners
  return (
    <section className="lb wrap" id="leaderboard">
      <Appear>
        <div className="eyebrow">01 — The ranking</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Who warmed the most
        </h2>
        <p className="sec-sub">
          {total} tracked flights across {owners.length} public-figure jets, ranked by combined warming
          (fuel CO₂ + contrails). Tiers, not a precise 1…N rank — magnitude reshuffles with the metric.
        </p>
      </Appear>

      <div className="lb-grid">
        <Appear className="lb-card lb-hero">
          <span className="stripe" style={{ background: stripeColor(first.tier) }} />
          <span className="ghost">01</span>
          <div className="lb-top">
            <div>
              <div className="lb-rank">Rank 01</div>
              <div className="lb-name">{first.owner}</div>
              <div className="lb-ac">
                {first.ac_type} · {first.flights} flights · {first.warm} warmed · {first.cool} cooled · {first.zero} ~none
              </div>
            </div>
            <div className="lb-val" style={{ textAlign: 'right' }}>
              <div className="t">
                {tonnes(first.combinedT * 1000)} <span className="u">t CO₂e</span>
              </div>
            </div>
          </div>
          <Mag pct={(first.combinedT / max) * 100} />
          <Chips o={first} />
        </Appear>

        {rest.map((o, i) => (
          <Appear key={o.owner} className="lb-card lb-row" delay={(i % 2) * 60}>
            <span className="stripe" style={{ background: stripeColor(o.tier) }} />
            <span className="ghost">{String(i + 2).padStart(2, '0')}</span>
            <div className="lb-top">
              <div>
                <div className="lb-rank">Rank {String(i + 2).padStart(2, '0')}</div>
                <div className="lb-name">{o.owner}</div>
                <div className="lb-ac">
                  {o.ac_type} · {o.flights} flights
                </div>
              </div>
              <div className="lb-val" style={{ textAlign: 'right' }}>
                <div className="t">
                  {tonnes(o.combinedT * 1000)} <span className="u">t</span>
                </div>
              </div>
            </div>
            <Mag pct={(o.combinedT / max) * 100} />
            <Chips o={o} />
          </Appear>
        ))}
      </div>
    </section>
  )
}
