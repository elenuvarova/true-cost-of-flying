import { useEffect, useState } from 'react'
import { useLenis } from './lib/scroll'
import { Flight, Horizon, aggregateOwners, loadFlights } from './lib/data'
import Hero from './components/Hero'
import Leaderboard from './components/Leaderboard'
import Explorer from './components/Explorer'

export default function App() {
  const [flights, setFlights] = useState<Flight[]>([])
  const [progress, setProgress] = useState(0)
  const horizon: Horizon = 'GWP100'

  useLenis(setProgress)
  useEffect(() => {
    loadFlights().then(setFlights)
  }, [])

  const owners = flights.length ? aggregateOwners(flights, horizon) : []

  return (
    <>
      <div className="bg-field" />
      <div className="bg-grain" />
      <div className="rail" style={{ width: `${progress * 100}%` }} />

      <main className="content">
        <Hero />
        <Leaderboard owners={owners} total={flights.length} />
        <Explorer flights={flights} horizon={horizon} />

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
