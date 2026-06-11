import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { TripsLayer } from '@deck.gl/geo-layers'
import { IconLayer, ScatterplotLayer } from '@deck.gl/layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import { efColor, RED, BLUE } from '../lib/colors'
import { loadTrack } from '../lib/data'
import { reduced } from '../lib/scroll'

const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

// white top-down airplane (points north) as a data-URI icon for the moving head-of-trail plane
const PLANE_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 32 32"><path fill="#ffffff" d="M16 2.6c-1 0-1.7 1.1-1.7 2.7v7.3L3.5 18v2.3l10.8-3.4V22L11 24.6v1.8l5-1.5 5 1.5v-1.8L17.7 22v-5.1l10.8 3.4V18L17.7 12.6V5.3c0-1.6-.7-2.7-1.7-2.7z"/></svg>'
const PLANE_ICON = 'data:image/svg+xml,' + encodeURIComponent(PLANE_SVG)

// position + heading of the drawing head at animation time t (segments are ~2-point trips, ordered)
function headAt(trips: Trip[], t: number) {
  const N = trips.length
  if (!N) return null
  const i = Math.max(0, Math.min(N - 1, Math.floor(t)))
  const path = trips[i].path
  const a = path[0]
  const b = path[path.length - 1]
  const f = Math.max(0, Math.min(1, t - i))
  const lon = a[0] + (b[0] - a[0]) * f
  const lat = a[1] + (b[1] - a[1]) * f
  // smooth the heading over ~4 segments so noisy short landing segments don't make the plane wobble
  const back = trips[Math.max(0, i - 4)].path[0]
  let dlon = lon - back[0]
  let dlat = lat - back[1]
  if (Math.abs(dlon) < 1e-7 && Math.abs(dlat) < 1e-7) {
    dlon = b[0] - a[0]
    dlat = b[1] - a[1]
  }
  const bearing = (Math.atan2(dlon * Math.cos((lat * Math.PI) / 180), dlat) * 180) / Math.PI
  return { lon, lat, bearing }
}

const MAP_BEARING = 0

const planeLayer = (head: { lon: number; lat: number; bearing: number } | null) =>
  new IconLayer({
    id: 'plane',
    data: head ? [head] : [],
    getPosition: (d: any) => [d.lon, d.lat],
    getIcon: () => ({ url: PLANE_ICON, width: 32, height: 32, anchorX: 16, anchorY: 16, mask: false }),
    getSize: 26,
    sizeUnits: 'pixels',
    getAngle: (d: any) => -d.bearing - MAP_BEARING,
    billboard: true,
    parameters: { depthTest: false },
  } as any)

type Trip = { path: [number, number][]; timestamps: number[]; color: [number, number, number] }
// C — bloom seed: where meaningful forcing forms. warm=red expands, cool=blue expands, as the head passes.
type Seed = { position: [number, number]; t0: number; warm: boolean; strength: number }

function build(gj: any): { trips: Trip[]; seeds: Seed[]; bounds: maplibregl.LngLatBoundsLike; n: number } {
  let minLon = 180, minLat = 90, maxLon = -180, maxLat = -90
  const seeds: Seed[] = []
  const trips: Trip[] = (gj?.features || [])
    .filter((f: any) => f?.geometry?.type === 'LineString' && Array.isArray(f.geometry.coordinates) && f.geometry.coordinates.length >= 2)
    .map((f: any, i: number) => {
      const coords: number[][] = f.geometry.coordinates
      const path = coords.map((c) => {
        minLon = Math.min(minLon, c[0]); maxLon = Math.max(maxLon, c[0])
        minLat = Math.min(minLat, c[1]); maxLat = Math.max(maxLat, c[1])
        return [c[0], c[1]] as [number, number]
      })
      const ef = f.properties?.ef_share ?? 0
      if (Math.abs(ef) > 0.012) {
        // a chain of small glows along the segment (not one big disc) → a soft aura
        // hugging the warming/cooling stretch of the actual track
        const m0 = Math.max(1, coords.length - 1)
        const step = Math.max(1, Math.floor(coords.length / 6))
        for (let j = 0; j < coords.length; j += step) {
          seeds.push({
            position: [coords[j][0], coords[j][1]],
            t0: i + j / m0,
            warm: ef > 0,
            strength: Math.min(1, Math.abs(ef) / 0.06),
          })
        }
      }
      const m = Math.max(1, coords.length - 1)
      return { path, timestamps: coords.map((_, j) => i + j / m), color: efColor(ef) }
    })
  return { trips, seeds, bounds: [[minLon, minLat], [maxLon, maxLat]], n: trips.length }
}

// three stacked, low-alpha discs per seed fake a radial falloff; the chain of seeds along the
// segment merges into one soft plume. Each glow grows in as the trail head passes its own t0.
const bloomLayers = (seeds: Seed[], t: number, total: number) => {
  const grow = Math.max(1.5, total * 0.015)
  const lit = (s: Seed) => Math.max(0, Math.min(1, (t - s.t0) / grow))
  const rgb = (s: Seed) => (s.warm ? RED : BLUE)
  const disc = (id: string, base: number, span: number, alpha: number) =>
    new ScatterplotLayer({
      id, data: seeds,
      getPosition: (d: Seed) => d.position,
      getRadius: (d: Seed) => (base + d.strength * span) * (0.4 + 0.6 * lit(d)),
      radiusUnits: 'pixels',
      getFillColor: (d: Seed) => [...rgb(d), Math.round(alpha * lit(d))] as any,
      stroked: false, parameters: { depthTest: false },
      updateTriggers: { getRadius: t, getFillColor: t },
    } as any)
  return [
    disc('bloom-wide', 16, 20, 7),
    disc('bloom-outer', 10, 14, 12),
    disc('bloom-mid', 6, 9, 24),
    disc('bloom-core', 3, 4, 64),
  ]
}

const layerAt = (trips: Trip[], n: number, t: number) =>
  new TripsLayer<Trip>({
    id: 'contrail',
    data: trips,
    getPath: (d) => d.path as any,
    getTimestamps: (d) => d.timestamps,
    getColor: (d) => d.color as any,
    widthMinPixels: 4,
    widthMaxPixels: 9,
    capRounded: true,
    jointRounded: true,
    trailLength: n,
    currentTime: t,
    fadeTrail: false,
  } as any)

export default function FlightMap({ flightId, owner, date }: { flightId: string; owner?: string; date?: string }) {
  const elRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const overlayRef = useRef<MapboxOverlay | null>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const seedsRef = useRef<Seed[]>([])
  const nRef = useRef(0)
  const boundsRef = useRef<maplibregl.LngLatBoundsLike | null>(null)
  const loadedRef = useRef(false)

  useEffect(() => {
    if (!elRef.current) return
    const map = new maplibregl.Map({
      container: elRef.current,
      style: DARK_STYLE,
      center: [-80, 32],
      zoom: 3.4,
      pitch: 46,
      bearing: MAP_BEARING,
      attributionControl: { compact: true },
      interactive: false, // decorative fly-along; keeps role="img"+aria-label honest (no hidden pan/zoom controls)
    })
    const overlay = new MapboxOverlay({ interleaved: true, layers: [] })
    map.addControl(overlay as any)
    map.on('load', () => {
      loadedRef.current = true
      if (boundsRef.current) map.fitBounds(boundsRef.current, { padding: 90, pitch: 46, bearing: MAP_BEARING, duration: 0 })
    })
    mapRef.current = map
    overlayRef.current = overlay
    return () => map.remove()
  }, [])

  useEffect(() => {
    let alive = true
    loadTrack(flightId).then((gj) => {
      if (!alive || !gj) return
      const { trips, seeds, bounds, n } = build(gj)
      nRef.current = n + 28
      boundsRef.current = bounds
      seedsRef.current = seeds
      setTrips(trips)
      if (mapRef.current && loadedRef.current)
        mapRef.current.fitBounds(bounds, { padding: 90, pitch: 46, bearing: MAP_BEARING, duration: 1200 })
    })
    return () => { alive = false }
  }, [flightId])

  useEffect(() => {
    if (!trips.length) return
    const total = nRef.current
    const overlay = overlayRef.current
    const seeds = seedsRef.current
    if (reduced()) {
      // fully drawn, every warming/cooling bloom lit, plane parked at the destination
      overlay?.setProps({ layers: [...bloomLayers(seeds, total, total), layerAt(trips, total, total), planeLayer(headAt(trips, total))] })
      return
    }
    // normalise so the whole contrail draws in ~8s regardless of segment count
    const step = total / (8 * 60)
    let t = 0
    let raf = 0
    let visible = true
    const io = new IntersectionObserver((es) => { visible = es[0]?.isIntersecting ?? true }, { threshold: 0.01 })
    if (elRef.current) io.observe(elRef.current)
    const tick = () => {
      if (visible) {
        t = (t + step) % total
        overlay?.setProps({ layers: [...bloomLayers(seeds, t, total), layerAt(trips, total, t), planeLayer(headAt(trips, t))] })
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); io.disconnect() }
  }, [trips])

  const label = owner
    ? `Flight-path map: ${owner}${date ? `, ${date}` : ''}. The contrail is coloured by where warming occurred — red warms, blue cools, amber is the fuel-CO₂ baseline. The figures are in the panel above this map.`
    : 'Flight-path map showing where contrail warming occurred along the route.'

  return <div ref={elRef} role="img" aria-label={label} style={{ position: 'absolute', inset: 0 }} />
}
