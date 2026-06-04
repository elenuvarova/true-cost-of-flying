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
        <path className="trail" d="M12 74 C 96 74, 178 56, 286 24" stroke="url(#trailH)" strokeWidth="5" strokeLinecap="round" />
        <g transform="translate(286 24) rotate(-17)">
          <path className="jet" d="M11 0 L-11 -8 L-4 0 L-11 8 Z" fill="#f4f8fc" />
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
