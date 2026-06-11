import { useEffect, useRef } from 'react'
import { reduced } from '../lib/scroll'
import type { Jet3D } from '../lib/jet3d'

// Awwwards-grade hero: the section pins to the screen and SCROLL FLIES THE PLANE.
// On load the jet takes off and inks the first stretch of contrail by itself (intro autopilot);
// after that the scroll position scrubs the flight across the full viewport — "Scroll to fly" is literal.
// The contrail spans the whole sky behind the headline: blue (cool) → amber (fuel) → warm red.

// Full-viewport sky in a 1440×900 box (preserveAspectRatio=slice crops gracefully on any screen).
// Phones crop the box to its central ~[515…925] band, so they get their own steeper climb
// that stays inside that band; the gradient is pinned to the active path's endpoints.
const SKY = { d: 'M-80 760 C 240 790, 520 740, 800 580 C 1040 442, 1230 320, 1530 150', g: [-80, 760, 1530, 150] }
const SKY_M = { d: 'M480 980 C 610 800, 690 630, 760 460 C 820 315, 870 185, 902 78', g: [480, 980, 902, 78] }
// jet glyph: sleek delta ("concorde") silhouette, drawn nose-up in a 32×32 box → rotate = tangent + 90°
const JET_D =
  'M16 1 C16.8 6 17 10 17 14 L17 15 C22 18 27 21.5 29.5 24.5 L29.5 26.5 L18.5 22.5 C18.2 24.5 17.8 26 17.3 27.5 L21.5 30 L21.5 31.5 L16 30 L10.5 31.5 L10.5 30 L14.7 27.5 C14.2 26 13.8 24.5 13.5 22.5 L2.5 26.5 L2.5 24.5 C5 21.5 10 18 15 15 L15 14 C15 10 15.2 6 16 1 Z'
const NOSE = 90
const INTRO_T = 0.22 // how far the autopilot flies before scroll takes over
const easeOut = (x: number) => 1 - Math.pow(1 - x, 3)

export default function Hero() {
  const secRef = useRef<HTMLElement>(null)
  const pinRef = useRef<HTMLDivElement>(null)
  const glowRef = useRef<SVGPathElement>(null)
  const midRef = useRef<SVGPathElement>(null)
  const coreRef = useRef<SVGPathElement>(null)
  const gradRef = useRef<SVGLinearGradientElement>(null)
  const jetRef = useRef<SVGGElement>(null)
  const cueRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const sec = secRef.current
    const pin = pinRef.current
    const glow = glowRef.current
    const mid = midRef.current
    const core = coreRef.current
    const grad = gradRef.current
    const jet = jetRef.current
    if (!sec || !pin || !glow || !mid || !core || !grad || !jet) return
    const strokes = [glow, mid]

    // pick the flight path for this screen and pin the gradient to its endpoints
    const mq = window.matchMedia('(max-width:720px)')
    let L = 0
    const apply = () => {
      const cfg = mq.matches ? SKY_M : SKY
      strokes.forEach((p) => p.setAttribute('d', cfg.d))
      core.setAttribute('d', cfg.d)
      const [x1, y1, x2, y2] = cfg.g
      grad.setAttribute('x1', String(x1)); grad.setAttribute('y1', String(y1))
      grad.setAttribute('x2', String(x2)); grad.setAttribute('y2', String(y2))
      L = mid.getTotalLength()
      strokes.forEach((p) => { p.style.strokeDasharray = String(L) })
    }
    apply()
    mq.addEventListener?.('change', apply)

    // 3D frosted jet everywhere except reduced-motion. The SVG glyph is hidden up front so it
    // never flashes before the lazy 3D chunk arrives; when the 3D jet is ready the take-off
    // replays from the start of the path — entering from beyond the screen edge.
    let jet3d: Jet3D | null = null
    let jet3dGone = false
    let start = 0
    if (!reduced()) {
      jet.style.display = 'none'
      import('../lib/jet3d').then((m) => m.mountJet3D(pin)).then((j) => {
        if (jet3dGone) { j.dispose(); return }
        jet3d = j
        start = 0 // replay the autopilot take-off with the 3D jet
      }).catch(() => { jet.style.display = '' }) // any WebGL/load failure → SVG glyph returns
    }

    // viewBox (1440×900, slice) → viewport px
    const toScreen = (x: number, y: number) => {
      const w = pin.clientWidth, h = pin.clientHeight
      const s = Math.max(w / 1440, h / 900)
      return { x: x * s + (w - 1440 * s) / 2, y: y * s + (h - 900 * s) / 2 }
    }

    let prevAng = 0
    let bank = 0
    const place = (t: number) => {
      const l = Math.max(0.5, t * L)
      const pt = mid.getPointAtLength(l)
      const back = mid.getPointAtLength(Math.max(0, l - 3))
      const ang = (Math.atan2(pt.y - back.y, pt.x - back.x) * 180) / Math.PI
      strokes.forEach((p) => { p.style.strokeDashoffset = String(L * (1 - t)) })
      // white-hot "fresh exhaust" segment that trails the jet and cools into the gradient
      const CORE = Math.min(80, L * 0.1)
      core.style.strokeDasharray = `${CORE} ${L + CORE}`
      core.style.strokeDashoffset = String(CORE - l)
      core.style.opacity = String(Math.min(0.85, t * 14))
      if (jet3d) {
        // bank into the turn: smoothed heading rate, clamped
        const dAng = ang - prevAng
        bank += (Math.max(-22, Math.min(22, dAng * 30)) - bank) * 0.08
        const s = toScreen(pt.x, pt.y)
        jet3d.place(s.x, s.y, ang, bank, t > 0.004)
      } else {
        jet.setAttribute('transform', `translate(${pt.x} ${pt.y}) rotate(${ang + NOSE}) scale(1.8) translate(-16 -16)`)
        jet.style.opacity = String(Math.min(1, t * 18))
      }
      prevAng = ang
    }

    if (reduced()) { place(1); return () => mq.removeEventListener?.('change', apply) }

    let raf = 0
    const tick = (now: number) => {
      if (!start) start = now
      // phones park the autopilot a touch earlier so the jet doesn't cover the scroll cue
      const intro = easeOut(Math.min(1, (now - start) / 2400)) * (mq.matches ? 0.15 : INTRO_T)
      // scroll scrub over the pinned distance (Lenis drives window scroll, so the rect is live)
      const r = sec.getBoundingClientRect()
      const scrollable = r.height - window.innerHeight
      const sp = scrollable > 0 ? Math.min(1, Math.max(0, -r.top / scrollable)) : 1
      // scroll takes over from the autopilot: full scrub maps to the whole flight
      if (r.bottom > 0) place(Math.max(intro, sp)) // skip work once the hero has scrolled away
      if (cueRef.current) cueRef.current.style.opacity = String(Math.max(0, 1 - sp * 5))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      mq.removeEventListener?.('change', apply)
      jet3dGone = true
      jet3d?.dispose()
    }
  }, [])

  return (
    <section ref={secRef} className="hero-stage">
      <div ref={pinRef} className="hero-pin">
        <svg className="hero-sky" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" fill="none" aria-hidden="true">
          <defs>
            <linearGradient ref={gradRef} id="skyTrail" gradientUnits="userSpaceOnUse" x1="-80" y1="760" x2="1530" y2="150">
              <stop offset="0" stopColor="#4fb0f5" stopOpacity="0" />
              <stop offset=".32" stopColor="#4fb0f5" stopOpacity=".55" />
              <stop offset=".62" stopColor="#e8b24a" />
              <stop offset=".85" stopColor="#ef6a43" />
              <stop offset="1" stopColor="#c81e3a" />
            </linearGradient>
          </defs>
          {/* wide soft underglow + colour body + white-hot fresh segment at the head */}
          <path ref={glowRef} className="sky-glow" d={SKY.d} stroke="url(#skyTrail)" strokeWidth="26" strokeLinecap="round" />
          <path ref={midRef} className="sky-mid" d={SKY.d} stroke="url(#skyTrail)" strokeWidth="6" strokeLinecap="round" />
          <path ref={coreRef} className="sky-core" d={SKY.d} stroke="#fff" strokeWidth="2.6" strokeLinecap="round" style={{ opacity: 0 }} />
          <g ref={jetRef} className="sky-jet" style={{ opacity: 0 }}>
            <path fill="#f4f8fc" d={JET_D} />
          </g>
        </svg>

        <div className="hero-copy wrap">
          <div className="eyebrow">Fuel CO₂ is only part of the story</div>
          <h1>
            The <span className="g">true cost</span>
            <br />
            of flying
          </h1>
          <p className="hero-sub">
            Every jet tracker shows one number: CO₂. But across aviation that’s only about <span className="em">a third</span> of
            the warming — the rest is mostly <span className="em">contrails</span>. Fly one real flight, and watch its
            contrail warming ink itself in — computed with CoCiP physics, not guessed.
          </p>
          <div className="scrollcue" ref={cueRef}>
            <span>Scroll to fly</span>
            <span className="dot" />
          </div>
        </div>
      </div>
    </section>
  )
}
