import { useEffect, useState } from 'react'
import { useLenis } from './lib/scroll'
import { Flight, Horizon, aggregateOwners, loadFlights } from './lib/data'
import Hero from './components/Hero'
import Leaderboard from './components/Leaderboard'
import Explorer from './components/Explorer'

export default function App() {
  const [flights, setFlights] = useState<Flight[]>([])
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')
  const [horizon, setHorizon] = useState<Horizon>('GWP100')
  const [progress, setProgress] = useState(0)

  useLenis(setProgress)
  useEffect(() => {
    loadFlights()
      .then((f) => { setFlights(f); setStatus('ok') })
      .catch(() => setStatus('error'))
  }, [])

  const owners = flights.length ? aggregateOwners(flights, horizon) : []

  return (
    <>
      <div className="bg-field" />
      <div className="bg-grain" />
      <div className="rail" style={{ width: `${progress * 100}%` }} />

      <main className="content">
        <Hero />

        {status === 'loading' && (
          <section className="wrap" style={{ padding: '5rem 0', minHeight: '40vh' }}>
            <p className="sec-sub" aria-live="polite">Loading flights…</p>
          </section>
        )}
        {status === 'error' && (
          <section className="wrap" style={{ padding: '5rem 0', minHeight: '40vh' }}>
            <p className="sec-sub" role="alert">
              Couldn’t load the flight data — please refresh. If it persists, the data file may be unavailable.
            </p>
          </section>
        )}
        {status === 'ok' && (
          <>
            <Leaderboard owners={owners} total={flights.length} />
            <Explorer flights={flights} horizon={horizon} onHorizon={setHorizon} />
          </>
        )}

        <footer>
          <div className="wrap">
            The total shown is <b style={{ color: 'var(--ink-2)' }}>fuel CO₂ + contrails only</b> — it omits NOx, water
            vapour and aerosols, so it is not the aviation-wide ~3× figure. Contrail warming carries ~70% uncertainty
            (IPCC “low confidence”). Aircraft, not people. Tracks from adsb.lol (ODbL-1.0) · ERA5 · OpenAP · pycontrails
            CoCiP. Non-commercial / educational.
          </div>
        </footer>
      </main>
    </>
  )
}
