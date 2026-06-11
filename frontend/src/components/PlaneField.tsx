// A — Ambient fleet. A few very faint aircraft drift across the page behind the content,
// each inking a thin contrail that fades toward its tail. Decorative only (aria-hidden),
// fully disabled under prefers-reduced-motion (see styles.css .planefield).
const FLIGHTS = [
  { top: '11%', dur: 62, delay: -4, scale: 1.0, op: 0.14, tilt: -7 },
  { top: '34%', dur: 82, delay: -34, scale: 0.66, op: 0.09, tilt: -4 },
  { top: '58%', dur: 70, delay: -52, scale: 0.86, op: 0.11, tilt: -11 },
  { top: '79%', dur: 96, delay: -16, scale: 0.52, op: 0.07, tilt: -3 },
]

// north-pointing top-down plane; rotated +90° in CSS so it flies east along its lane
const PLANE =
  'M16 2.6c-1 0-1.7 1.1-1.7 2.7v7.3L3.5 18v2.3l10.8-3.4V22L11 24.6v1.8l5-1.5 5 1.5v-1.8L17.7 22v-5.1l10.8 3.4V18L17.7 12.6V5.3c0-1.6-.7-2.7-1.7-2.7z'

export default function PlaneField() {
  return (
    <div className="planefield" aria-hidden="true">
      {FLIGHTS.map((f, i) => (
        <div
          key={i}
          className="pf-lane"
          style={{ top: f.top, animationDuration: `${f.dur}s`, animationDelay: `${f.delay}s`, opacity: f.op }}
        >
          <div className="pf-craft" style={{ transform: `scale(${f.scale}) rotate(${f.tilt}deg)` }}>
            <span className="pf-trail" />
            <svg className="pf-plane" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
              <path d={PLANE} />
            </svg>
          </div>
        </div>
      ))}
    </div>
  )
}
