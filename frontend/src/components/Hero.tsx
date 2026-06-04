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
        {/* SF Symbols airplane glyph, rotate 30 — measured to lie along the contrail tangent */}
        <g transform="translate(283 25) rotate(30) scale(2.35) translate(-8 -8)">
          <path
            className="jet"
            fill="#f4f8fc"
            d="M12.2027 1.12512C13.2573 0.0784756 14.6089 -0.33575 15.2574 0.30481C15.8978 0.953287 15.4829 2.30486 14.4361 3.3595L12.2027 5.59387C11.898 5.89851 11.8278 6.06274 11.8589 6.46106L12.1949 14.2189C12.2027 14.4687 12.1322 14.6798 11.9761 14.8439L11.3277 15.4767C11.187 15.6251 10.9683 15.5783 10.8902 15.3517L8.57767 9.21887L5.45267 11.7032L6.2808 14.5392C6.35107 14.75 6.28836 14.9221 6.10892 15.1017L5.86674 15.3439C5.71834 15.4922 5.54639 15.4922 5.39799 15.3439L0.218299 10.1642C0.0698624 10.0158 0.0698624 9.84389 0.218299 9.69544L0.460487 9.46106C0.64006 9.27382 0.812169 9.21891 1.02299 9.28137L3.85892 10.1173L6.3433 6.9845L0.210487 4.672C-0.0160757 4.59388 -0.0629505 4.38294 0.085487 4.2345L0.726112 3.58606C0.88233 3.43004 1.09347 3.35951 1.3433 3.36731L9.10111 3.71106C9.49923 3.73442 9.66372 3.66408 9.9683 3.3595L12.2027 1.12512Z"
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
