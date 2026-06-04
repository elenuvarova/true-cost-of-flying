import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { TripsLayer } from '@deck.gl/geo-layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import { efColor } from '../lib/colors'
import { loadTrack } from '../lib/data'

const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

type Trip = { path: [number, number][]; timestamps: number[]; color: [number, number, number] }

function build(gj: any): { trips: Trip[]; bounds: maplibregl.LngLatBoundsLike; n: number } {
  let minLon = 180, minLat = 90, maxLon = -180, maxLat = -90
  const trips: Trip[] = gj.features.map((f: any, i: number) => {
    const coords: number[][] = f.geometry.coordinates
    const path = coords.map((c) => {
      minLon = Math.min(minLon, c[0]); maxLon = Math.max(maxLon, c[0])
      minLat = Math.min(minLat, c[1]); maxLat = Math.max(maxLat, c[1])
      return [c[0], c[1]] as [number, number]
    })
    const m = Math.max(1, coords.length - 1)
    return { path, timestamps: coords.map((_, j) => i + j / m), color: efColor(f.properties?.ef_share ?? 0) }
  })
  return { trips, bounds: [[minLon, minLat], [maxLon, maxLat]], n: gj.features.length }
}

export default function FlightMap({ flightId }: { flightId: string }) {
  const elRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const overlayRef = useRef<MapboxOverlay | null>(null)
  const [trips, setTrips] = useState<Trip[]>([])
  const nRef = useRef(0)
  const boundsRef = useRef<maplibregl.LngLatBoundsLike | null>(null)
  const loadedRef = useRef(false)

  // init map once
  useEffect(() => {
    if (!elRef.current) return
    const map = new maplibregl.Map({
      container: elRef.current,
      style: DARK_STYLE,
      center: [-80, 32],
      zoom: 3.4,
      pitch: 46,
      bearing: -10,
      attributionControl: true,
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

  // load track on flight change
  useEffect(() => {
    let alive = true
    loadTrack(flightId).then((gj) => {
      if (!alive || !gj) return
      const { trips, bounds, n } = build(gj)
      nRef.current = n
      boundsRef.current = bounds
      setTrips(trips)
      if (mapRef.current && loadedRef.current)
        mapRef.current.fitBounds(bounds, { padding: 90, pitch: 46, bearing: -10, duration: 1200 })
    })
    return () => { alive = false }
  }, [flightId])

  // animate the draw
  useEffect(() => {
    if (!trips.length) return
    const N = nRef.current
    const PAD = 28
    let t = 0
    let raf = 0
    const tick = () => {
      t = (t + 0.4) % (N + PAD)
      overlayRef.current?.setProps({
        layers: [
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
            trailLength: N + PAD,
            currentTime: t,
            fadeTrail: false,
          } as any),
        ],
      })
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [trips])

  return <div ref={elRef} style={{ position: 'absolute', inset: 0 }} />
}
