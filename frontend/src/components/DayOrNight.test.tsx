import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Flight, nightSplit } from '../lib/data'
import DayOrNight from './DayOrNight'

const flight = (o: Partial<Flight>): Flight => ({
  flight_id: 'x_1',
  owner_label: 'X',
  registration: 'N1',
  ac_type: 'Boeing 757-200',
  dep_time: null,
  date: '2025-01-01',
  route: '',
  fuel_co2_kg: 1000,
  contrail_ef_joules: 0,
  contrail_co2e_low: 0,
  contrail_co2e_central: 0,
  contrail_co2e_high: 0,
  contrail_co2e_gwp20_central: 0,
  contrail_pct_of_fuel: 0,
  bizjet_alt_flag: false,
  proxy_type_flag: false,
  coverage_gap_flag: false,
  tier: 'high',
  night_pct_of_waypoints: null,
  night_class: null,
  ...o,
})

const FLIGHTS: Flight[] = [
  flight({ flight_id: 'n1', night_class: 'night', contrail_ef_joules: 3e14, contrail_co2e_central: 90000 }),
  flight({ flight_id: 'n2', night_class: 'night', contrail_ef_joules: 1e14, contrail_co2e_central: 30000 }),
  flight({ flight_id: 'd1', night_class: 'day', contrail_ef_joules: -2e14, contrail_co2e_central: -60000 }),
  flight({ flight_id: 'd2', night_class: 'day', contrail_ef_joules: 5e12, contrail_co2e_central: 1500 }),
  flight({ flight_id: 'z1', night_class: 'day', contrail_ef_joules: 0, contrail_co2e_central: 0 }),
  flight({ flight_id: 'm1', night_class: 'mixed', contrail_ef_joules: 1e13, contrail_co2e_central: 3000 }),
]

describe('nightSplit', () => {
  it('returns night, mixed and day in that order', () => {
    expect(nightSplit(FLIGHTS, 'GWP100').map((g) => g.cls)).toEqual(['night', 'mixed', 'day'])
  })

  it('counts only flights that formed a contrail', () => {
    const day = nightSplit(FLIGHTS, 'GWP100').find((g) => g.cls === 'day')!
    expect(day.flights).toBe(2) // z1 formed nothing and is excluded
  })

  it('splits warmed and cooled by the sign of the forcing', () => {
    const [night, , day] = nightSplit(FLIGHTS, 'GWP100')
    expect(night).toMatchObject({ warmed: 2, cooled: 0 })
    expect(day).toMatchObject({ warmed: 1, cooled: 1 })
  })

  it('sums CO₂e in tonnes for the chosen horizon', () => {
    const night = nightSplit(FLIGHTS, 'GWP100')[0]
    expect(night.co2eT).toBeCloseTo(120)
  })

  it('ignores flights with no classification', () => {
    const unclassified = [...FLIGHTS, flight({ flight_id: 'u1', contrail_ef_joules: 9e14 })]
    const total = nightSplit(unclassified, 'GWP100').reduce((s, g) => s + g.flights, 0)
    expect(total).toBe(5)
  })
})

describe('DayOrNight', () => {
  it('states the night result', () => {
    render(<DayOrNight flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('night-line')).toHaveTextContent(/2 of 2/)
  })

  it('carries a text equivalent for the chart', () => {
    render(<DayOrNight flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('diverging-alt')).toHaveTextContent(/night/i)
  })

  it('discloses the night-selection bias', () => {
    render(<DayOrNight flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByText(/deliberately harvested/i)).toBeInTheDocument()
  })

  it('renders nothing when no flight is classified', () => {
    const { container } = render(<DayOrNight flights={[flight({})]} horizon="GWP100" />)
    expect(container).toBeEmptyDOMElement()
  })
})
