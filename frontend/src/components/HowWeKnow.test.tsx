import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Flight } from '../lib/data'
import HowWeKnow from './HowWeKnow'

const flight = (o: Partial<Flight>): Flight => ({
  flight_id: 'x_1', owner_label: 'X', registration: 'N1', ac_type: 'B752', dep_time: null,
  date: '2025-01-01', route: '', fuel_co2_kg: 10000, contrail_ef_joules: 0,
  contrail_co2e_low: 0, contrail_co2e_central: 0, contrail_co2e_high: 0,
  contrail_co2e_gwp20_central: 0, contrail_pct_of_fuel: 0, bizjet_alt_flag: false,
  proxy_type_flag: false, coverage_gap_flag: false, tier: 'high',
  night_pct_of_waypoints: null, night_class: null, ...o,
})

const FLIGHTS = [
  flight({ flight_id: 'a', contrail_ef_joules: 1e14, contrail_co2e_central: 30000, contrail_co2e_low: 25000, contrail_co2e_high: 36000 }),
  flight({ flight_id: 'b' }),
  flight({ flight_id: 'c', bizjet_alt_flag: true }),
  flight({ flight_id: 'd', proxy_type_flag: true }),
]

describe('HowWeKnow', () => {
  it('reports how many flights formed a contrail', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-incidence')).toHaveTextContent('1 of 4')
  })

  it('reports the flagged share', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-flagged')).toHaveTextContent('2 of 4')
  })

  it('draws the uncertainty band around the total', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-band')).toHaveTextContent(/25\.0/)
    expect(screen.getByTestId('hwk-band')).toHaveTextContent(/36\.0/)
  })

  it('states what is not counted', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-excluded')).toHaveTextContent(/NOx/)
    expect(screen.getByTestId('hwk-excluded')).toHaveTextContent(/not the aviation-wide/i)
  })

  it('discloses the night-selection bias', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-bias')).toHaveTextContent(/deliberately harvested/i)
  })

  it('quantifies the night weighting as a count, not a phrase', () => {
    const mixed = [
      flight({ flight_id: 'n1', night_class: 'night' }),
      flight({ flight_id: 'n2', night_class: 'night' }),
      flight({ flight_id: 'd1', night_class: 'day' }),
    ]
    render(<HowWeKnow flights={mixed} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-bias')).toHaveTextContent('2 of 3')
  })

  it('keeps the band ordered low-to-high even when the net is negative', () => {
    const cooling = [
      flight({ flight_id: 'k', contrail_ef_joules: -1e14, contrail_co2e_central: -30000, contrail_co2e_low: -36000, contrail_co2e_high: -25000 }),
    ]
    render(<HowWeKnow flights={cooling} horizon="GWP100" />)
    const band = screen.getByTestId('hwk-band').textContent!
    const nums = [...band.matchAll(/-?[\d.]+/g)].map((m) => parseFloat(m[0].replace('−', '-')))
    expect(nums[0]).toBeLessThanOrEqual(nums[nums.length - 1])
  })
})
