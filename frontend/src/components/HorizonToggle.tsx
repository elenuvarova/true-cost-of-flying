import { Horizon } from '../lib/data'

// Lifted out of Explorer so the ranking section can carry the same control:
// the reshuffle caption changes with the horizon (5 of 11 at GWP100, 6 at
// GWP20), so the reader needs the control where they read the claim.
export default function HorizonToggle({
  horizon,
  onHorizon,
  note,
}: {
  horizon: Horizon
  onHorizon: (h: Horizon) => void
  note?: string
}) {
  return (
    <div className="hzrow">
      <div className="hztoggle" role="group" aria-label="Time horizon">
        {(['GWP100', 'GWP20'] as Horizon[]).map((h) => (
          <button
            key={h}
            className={h === horizon ? 'on' : ''}
            aria-pressed={h === horizon}
            onClick={() => onHorizon(h)}
          >
            {h}
          </button>
        ))}
      </div>
      {note && <p className="hz-note">{note}</p>}
    </div>
  )
}
