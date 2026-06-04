import { useEffect, useRef, useState } from 'react'
import Lenis from 'lenis'

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Physics smooth-scroll (the substrate every premium scroll piece sits on). Also exposes a
// 0..1 page-scroll progress for the top rail.
export function useLenis(onProgress?: (p: number) => void) {
  useEffect(() => {
    if (reduced()) {
      const onScroll = () => {
        const h = document.documentElement
        onProgress?.(h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight))
      }
      window.addEventListener('scroll', onScroll, { passive: true })
      return () => window.removeEventListener('scroll', onScroll)
    }
    const lenis = new Lenis({ lerp: 0.1, smoothWheel: true, wheelMultiplier: 1 })
    lenis.on('scroll', (e: any) => onProgress?.(e.progress ?? 0))
    let raf = 0
    const loop = (t: number) => {
      lenis.raf(t)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
    }
  }, [])
}

// Add `.in` when an element scrolls into view (one-shot). Cheap, 60fps, reduced-motion safe.
export function useReveal<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (reduced()) {
      el.classList.add('in')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries)
          if (e.isIntersecting) {
            e.target.classList.add('in')
            io.unobserve(e.target)
          }
      },
      { threshold: 0.18, rootMargin: '0px 0px -8% 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return ref
}

const easeOutCubic = (p: number) => 1 - Math.pow(1 - p, 3)
const easeOutBack = (p: number) => {
  const c1 = 1.70158, c3 = c1 + 1
  return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2) // overshoots past 1 then settles
}

// Eased count-up: animates 0→target the first time it enters view, then from the PREVIOUS
// value→target on subsequent target changes (so a horizon/flight switch reads as a deliberate
// move, never a reset glitch). Respects reduced motion (snaps).
export function useCountUp(target: number, dur = 1400, overshoot = false) {
  const [val, setVal] = useState(0)
  const ref = useRef<HTMLElement>(null)
  const valRef = useRef(0)
  const startedRef = useRef(false)
  useEffect(() => {
    valRef.current = val
  })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (reduced()) { setVal(target); valRef.current = target; return }
    const ease = overshoot ? easeOutBack : easeOutCubic
    let raf = 0
    const run = (from: number) => {
      const t0 = performance.now()
      const step = (now: number) => {
        const p = Math.min(1, (now - t0) / dur)
        setVal(from + (target - from) * ease(p))
        if (p < 1) raf = requestAnimationFrame(step)
        else setVal(target)
      }
      raf = requestAnimationFrame(step)
    }
    if (!startedRef.current) {
      const io = new IntersectionObserver(
        (entries) => {
          for (const e of entries)
            if (e.isIntersecting && !startedRef.current) {
              startedRef.current = true
              run(0)
            }
        },
        { threshold: 0.4 },
      )
      io.observe(el)
      return () => { io.disconnect(); cancelAnimationFrame(raf) }
    }
    run(valRef.current)
    return () => cancelAnimationFrame(raf)
  }, [target, dur, overshoot])
  return { val, ref }
}
