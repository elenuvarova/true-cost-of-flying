export default function Hero() {
  return (
    <section className="hero wrap">
      <div className="eyebrow">Fuel CO₂ is only part of the story</div>
      <h1>
        The <span className="g">true cost</span>
        <br />
        of flying
      </h1>
      <svg className="hero-plane" viewBox="0 0 300 96" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="trailH" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="#5aa0e0" stopOpacity="0" />
            <stop offset=".4" stopColor="#5aa0e0" stopOpacity=".5" />
            <stop offset=".78" stopColor="#ef6a43" />
            <stop offset="1" stopColor="#e8b24a" />
          </linearGradient>
        </defs>
        <path className="trail" d="M12 74 C 96 74, 178 56, 282 26" stroke="url(#trailH)" strokeWidth="5" strokeLinecap="round" />
        {/* up-pointing airplane (same glyph as the favicon + map) rotated to the contrail's tangent (~−16°) */}
        <g transform="translate(284 23) rotate(74) scale(0.82) translate(-16 -16)">
          <path
            className="jet"
            fill="#f4f8fc"
            d="M16 2.6c-1 0-1.7 1.1-1.7 2.7v7.3L3.5 18v2.3l10.8-3.4V22L11 24.6v1.8l5-1.5 5 1.5v-1.8L17.7 22v-5.1l10.8 3.4V18L17.7 12.6V5.3c0-1.6-.7-2.7-1.7-2.7z"
          />
        </g>
      </svg>
      <p className="hero-sub">
        Every jet tracker shows one number: CO₂. But across aviation that’s only about <span className="em">a third</span> of
        the warming — the rest is mostly <span className="em">contrails</span>. Fly one real flight, and watch its
        contrail warming ink itself in — computed with CoCiP physics, not guessed.
      </p>
      <div className="scrollcue">
        <span>Scroll to fly</span>
        <span className="dot" />
      </div>
    </section>
  )
}
