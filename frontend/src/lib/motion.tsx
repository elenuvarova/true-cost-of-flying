// Motion, kept off the critical path.
//
// `motion.div` pulls the whole feature set into the entry chunk (~34 KB gzip),
// which would blow the 70 KB budget. `LazyMotion` + `m` ships a small stub and
// fetches the rest as its own chunk after first paint. domMax (not domAnimation)
// because the leaderboard reorder needs layout animations.
import { LazyMotion } from 'motion/react'

// Must point at a distinct module (see lib/motion-features.ts) — importing
// 'motion/react' here would not split, since it is already imported above.
const loadFeatures = () => import('./motion-features').then((mod) => mod.default)

export { m } from 'motion/react'

export default function Motion({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={loadFeatures} strict>
      {children}
    </LazyMotion>
  )
}
