import '@testing-library/jest-dom/vitest'

// jsdom has no IntersectionObserver. useReveal (lib/scroll.ts) and useCountUp
// both use one; components must mount in tests, and reveal-gated content must
// be visible, so the stub reports every observed element as intersecting.
// (guarded via globalThis, not `in window` — the `in` narrowing collapses
// `window` to `never` inside the block and breaks tsc.)
if (typeof globalThis.IntersectionObserver === 'undefined') {
  class StubIntersectionObserver implements IntersectionObserver {
    readonly root = null
    readonly rootMargin = ''
    readonly thresholds: ReadonlyArray<number> = []
    constructor(private cb: IntersectionObserverCallback) {}
    observe(target: Element) {
      this.cb([{ isIntersecting: true, target } as IntersectionObserverEntry], this)
    }
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
      return []
    }
  }
  window.IntersectionObserver = StubIntersectionObserver as any
  globalThis.IntersectionObserver = StubIntersectionObserver as any
}

// jsdom has no rAF-driven layout; Motion's layout animations and useCountUp
// both schedule through it. Run callbacks on a macrotask so effects settle.
if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = ((cb: FrameRequestCallback) => setTimeout(() => cb(performance.now()), 0)) as any
  window.cancelAnimationFrame = ((id: number) => clearTimeout(id)) as any
}

// jsdom has no matchMedia; reduced() in lib/scroll.ts calls it.
if (!window.matchMedia) {
  window.matchMedia = ((q: string) => ({
    matches: false,
    media: q,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return false
    },
  })) as any
}
