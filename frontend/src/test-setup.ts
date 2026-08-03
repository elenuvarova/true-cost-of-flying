import '@testing-library/jest-dom/vitest'

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
