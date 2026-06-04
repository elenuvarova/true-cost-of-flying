// Data layer — fetches the static JSON exported from the parquet pipeline, plus helpers.
export type Horizon = 'GWP100' | 'GWP20'

export interface Flight {
  flight_id: string
  owner_label: string
  registration: string
  ac_type: string
  dep_time: string | null
  date: string
  route: string
  fuel_co2_kg: number
  contrail_ef_joules: number
  contrail_co2e_low: number
  contrail_co2e_central: number
  contrail_co2e_high: number
  contrail_co2e_gwp20_central: number
  contrail_pct_of_fuel: number
  bizjet_alt_flag: boolean
  proxy_type_flag: boolean
  coverage_gap_flag: boolean
  tier: string
}

export interface OwnerAgg {
  owner: string
  ac_type: string
  flights: number
  fuelT: number
  contrailT: number
  combinedT: number
  warm: number
  cool: number
  zero: number
  bizjet: boolean
  proxy: boolean
  tier: 'high' | 'med' | 'low'
}

export const contrailKg = (f: Flight, h: Horizon) =>
  h === 'GWP20' ? f.contrail_co2e_gwp20_central : f.contrail_co2e_central

export const tonnes = (kg: number, dp = 1) =>
  `${(kg / 1000).toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp })}`

export async function loadFlights(): Promise<Flight[]> {
  const r = await fetch('./data/leaderboard.json')
  return r.json()
}
export async function loadComparators(): Promise<Flight[]> {
  try {
    const r = await fetch('./data/comparators.json')
    return r.ok ? r.json() : []
  } catch {
    return []
  }
}
export async function loadTrack(flightId: string): Promise<any | null> {
  try {
    const r = await fetch(`./data/tracks/${flightId}.geojson`)
    return r.ok ? r.json() : null
  } catch {
    return null
  }
}

const W = 100 // kg threshold for warm/cool classification

export function aggregateOwners(flights: Flight[], h: Horizon): OwnerAgg[] {
  const by = new Map<string, Flight[]>()
  for (const f of flights) (by.get(f.owner_label) ?? by.set(f.owner_label, []).get(f.owner_label)!).push(f)
  const rows: Omit<OwnerAgg, 'tier'>[] = []
  for (const [owner, fs] of by) {
    const fuelKg = fs.reduce((s, f) => s + f.fuel_co2_kg, 0)
    const contrailKgSum = fs.reduce((s, f) => s + contrailKg(f, h), 0)
    rows.push({
      owner,
      ac_type: fs[0].ac_type,
      flights: fs.length,
      fuelT: fuelKg / 1000,
      contrailT: contrailKgSum / 1000,
      combinedT: (fuelKg + contrailKgSum) / 1000,
      warm: fs.filter((f) => f.contrail_co2e_central > W).length,
      cool: fs.filter((f) => f.contrail_co2e_central < -W).length,
      zero: fs.filter((f) => Math.abs(f.contrail_co2e_central) <= W).length,
      bizjet: fs.some((f) => f.bizjet_alt_flag),
      proxy: fs.some((f) => f.proxy_type_flag),
    })
  }
  rows.sort((a, b) => b.combinedT - a.combinedT)
  const n = rows.length
  return rows.map((r, i) => ({
    ...r,
    tier: i < n / 3 ? 'high' : i >= (2 * n) / 3 ? 'low' : 'med',
  }))
}

export function flightsFor(flights: Flight[], owner: string, h: Horizon): Flight[] {
  return flights
    .filter((f) => f.owner_label === owner)
    .sort((a, b) => b.fuel_co2_kg + contrailKg(b, h) - (a.fuel_co2_kg + contrailKg(a, h)))
}

// the most telling flight = largest |contrail| (GWP100 central, sign-stable)
export function standoutFlight(flights: Flight[]): Flight {
  return flights.reduce((best, f) =>
    Math.abs(f.contrail_co2e_central) > Math.abs(best.contrail_co2e_central) ? f : best,
  )
}

// Featured flyers — verified, fact-checked copy carried over from the audited dataset.
export const FEATURED_ORDER = ['Donald Trump', 'Taylor Swift', 'Drake', 'Elon Musk', 'Bill Gates']

export const SHORT: Record<string, string> = {
  'New England Patriots': 'Patriots',
  'Phil Knight (Nike)': 'Phil Knight',
  'Mark Zuckerberg': 'Zuckerberg',
}
export const short = (o: string) => SHORT[o] ?? o

export interface Portrait {
  badge: string
  ac: string
  headline: string
  framing: string
}
export const PORTRAITS: Record<string, Portrait> = {
  'Donald Trump': {
    badge: 'one night flight = all the warming',
    ac: 'Boeing 757-200 · in-domain (most trustworthy numbers)',
    headline:
      'Six of seven 757 flights formed almost nothing — then one deep-night NY→Palm Beach run added +90 t, ~2.4× that flight’s own fuel CO₂.',
    framing:
      'All seven tracked flights are on the same in-domain Boeing 757-200, cruising near 38,000 ft (below CoCiP’s ~13 km cap) — the cleanest, least-caveated numbers in the set. Fuel is blunt: 264.6 t of CO₂. Contrails tell the opposite story: six of seven formed essentially zero, and effectively all 90.2 t of contrail CO₂e came from one deep-night run crossing a ~130 km ice-supersaturated band. Across all 7 flights that lifts warming +34% on top of fuel — the honest per-flight 30–60% GWP100 range, NOT the ~3× whole-fleet figure. A second deep-night flight formed zero: the trigger is crossing ice-supersaturated air, not night alone.',
  },
  'Taylor Swift': {
    badge: 'daytime standout',
    ac: 'Dassault Falcon 7X',
    headline:
      'Nine of twelve flights formed none — but a daytime Tennessee→Montana leg added +12.1 t, almost matching its 12.7 t of fuel (~2× that flight).',
    framing:
      'Across 12 flights the Falcon 7X burned 121.8 t of fuel CO₂. Nine formed essentially none (a power-law reality), but three warmed, adding 18.4 t CO₂e. The standout daytime Tennessee→Montana leg put 12.1 t of contrail warming almost on top of its 12.7 t of fuel — roughly a 2× flight. The jet climbed to 13.1 km, just past CoCiP’s cap, so it’s flagged UNDER-counted, not extrapolated — the real warming is at least this.',
  },
  Drake: {
    badge: 'clean · day ↔ night',
    ac: 'Boeing 767-200ER · in-domain → most trustworthy',
    headline:
      'Same Toronto↔Houston route, opposite sign: the day leg net-cooled −10.3 t, the night return warmed +1.6 t. The cleanest day/night proof in the set.',
    framing:
      'Across 7 flights on his Boeing 767, Drake’s engines put 277.8 t of CO₂ into the air. Five of seven formed essentially none. Only two legs produced meaningful forcing, opposite ways. The net came out slightly cooling (~−8.6 t at GWP100), almost entirely one daytime Toronto→Houston leg whose ice cloud sat in full sunlight and reflected more than it trapped (−10.3 t); the night return did the opposite (+1.6 t). Same city-pair, opposite sign, purely from time of day. All in-domain, so unlike the bizjets these are not under-counted.',
  },
  'Elon Musk': {
    badge: 'cuts both ways',
    ac: 'Gulfstream G650ER',
    headline:
      'Contrails cut both ways — two night flights warmed, two daytime legs net-cooled (down to −19 t). Read the net as a mix, not “climate-positive”.',
    framing:
      'Across 11 flights on a single G650ER, the certain cost is ~117.5 t of fuel CO₂. Seven formed little or none; two night flights warmed (up to +7 t), two daytime flights reflected enough sunlight to net-cool (down to −19 t). Summed, the contrail term is slightly negative (~−18.7 t) — but that rests on just two daytime flagged flights above the cap, so read it as a mix, not climate-positive. The cleanest case is an in-domain night flight whose ~7 t contrail roughly equals its ~6.8 t fuel — which is exactly why a raw +103% must not be headlined.',
  },
  'Bill Gates': {
    badge: 'night standout',
    ac: 'Gulfstream G650ER',
    headline:
      'Mostly clean — 7 of 10 flights formed none. Two night flights warmed (+5.6 t standout on a large fuel base); one daytime leg cooled.',
    framing:
      'Across 10 flights the G650ER burned 106.2 t of CO₂. Contrails were a small, lumpy add-on: 7 of 10 formed essentially none, 2 night flights warmed (+5.56 and +2.74 t), 1 daytime flight cooled slightly (−1.39 t), netting ~+6.9 t. The standout — a transcontinental redeye adding 5.56 t on 17.2 t of fuel (+32%, a stable ratio on a large denominator) — shows the climate-advocate tension honestly.',
  },
}
