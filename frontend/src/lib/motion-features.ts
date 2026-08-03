// Motion's animation features, isolated in their own module so Rollup can put
// them in their own chunk.
//
// This file exists purely for code-splitting. `import('motion/react')` from
// inside lib/motion.tsx would NOT split, because that file already imports
// 'motion/react' statically for LazyMotion and `m` — Rollup would see one
// module and emit one chunk. Pointing the dynamic import at a distinct module
// is what actually defers the feature bundle.
//
// domMax (not domAnimation) because the leaderboard reorder needs layout
// animations.
export { domMax as default } from 'motion/react'
