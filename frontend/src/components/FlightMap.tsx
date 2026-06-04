import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { TripsLayer } from '@deck.gl/geo-layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import { efColor } from '../lib/colors'
import { loadTrack } from '../lib/data'
import { reduced } from '../lib/scroll'

const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

type Trip = { path: [number, number][]; timestamps: number[]; color: [number, number, number] }

function build(gj: any): { trips: Trip[]; bounds: maplibregl.LngLatBoundsLike; n: number } {
  let minLon = 180, minLat = 90, maxLon = -180, maxLat = -90
  const trips: Trip[] = (gj?.features || [])
    .filter((f: any) => f?.geometry?.type === 'LineString' && Array.isArray(f.geometry.coordinates) && f.geometry.coordinates.length >= 2)
    .map((f: any, i: number) => {
      const coords: number[][] = f.geometry.coordinates
      const path = coords.map((c) => {
        minLon = Math.min(minLon, c[0]); maxLon = Math.max(maxLon, c[0])
        minLat = Math.min(minLat, c[1]); maxLat = Math.max(maxLat, c[1])
        return [c[0], c[1]] as [number, number]
      })
      const m = Math.max(1, coords.length - 1)
      return { path, timestamps: coords.map((_, j) => i + j / m), color: efColor(f.properties?.ef_share ?? 0) }
    })
  return { trips, bounds: [[minLon, minLat], [maxLon, maxLat]], n: trips.length }
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
      bearing: -10,
      attributionControl: { compact: true },
    })
    const overlay = new MapboxOverlay({ interleaved: true, layers: [] })
    map.addControl(overlay as any)
    map.on('load', () => {
      loadedRef.current = true
      if (boundsRef.current) map.fitBounds(boundsRef.current, { padding: 90, pitch: 46, bearing: -10, duration: 0 })
    })
    mapRef.current = map
    overlayRef.current = overlay
    return () => map.remove()
  }, [])

  useEffect(() => {
    let alive = true
    loadTrack(flightId).then((gj) => {
      if (!alive || !gj) return
      const { trips, bounds, n } = build(gj)
      nRef.current = n + 28
      boundsRef.current = bounds
      setTrips(trips)
      if (mapRef.current && loadedRef.current)
        mapRef.current.fitBounds(bounds, { padding: 90, pitch: 46, bearing: -10, duration: 1200 })
    })
    return () => { alive = false }
  }, [flightId])

  useEffect(() => {
    if (!trips.length) return
    const total = nRef.current
    const overlay = overlayRef.current
    if (reduced()) {
      overlay?.setProps({ layers: [layerAt(trips, total, total)] }) // fully drawn, static
      return
    }
    // normalise so the whole contrail draws in ~4.5s regardless of segment count
    const step = total / (4.5 * 60)
    let t = 0
    let raf = 0
    let visible = true
    const io = new IntersectionObserver((es) => { visible = es[0]?.isIntersecting ?? true }, { threshold: 0.01 })
    if (elRef.current) io.observe(elRef.current)
    const tick = () => {
      if (visible) {
        t = (t + step) % total
        overlay?.setProps({ layers: [layerAt(trips, total, t)] })
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
