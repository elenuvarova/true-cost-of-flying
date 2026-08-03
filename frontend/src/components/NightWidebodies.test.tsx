import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import NightWidebodies from './NightWidebodies'

const ROWS = [
  { flight_id: 'a_1', owner_label: 'F-GSQK (B77W)', ac_type: 'BOEING 777-300ER', fuel_co2_kg: 274343.2, contrail_co2e_central: 158633.6, contrail_pct_of_fuel: 57.8 },
  { flight_id: 'b_1', owner_label: 'G-XWBC (A35K)', ac_type: 'AIRBUS A-350-1000', fuel_co2_kg: 234674.8, contrail_co2e_central: 193180.8, contrail_pct_of_fuel: 82.3 },
  { flight_id: 'c_1', owner_label: 'G-ZBKF (B789)', ac_type: 'BOEING 787-9', fuel_co2_kg: 154466.4, contrail_co2e_central: 8737.2, contrail_pct_of_fuel: 5.7 },
]

afterEach(() => vi.unstubAllGlobals())

const stubFetch = (rows: unknown) =>
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => rows }))

describe('NightWidebodies', () => {
  it('lists every comparator flight', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    await waitFor(() => expect(screen.getAllByTestId('cmp-row')).toHaveLength(3))
  })

  it('shows the aggregate ratio computed from the rows, not a hardcoded number', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    // (158633.6 + 193180.8 + 8737.2) / (274343.2 + 234674.8 + 154466.4) = 54.4%
    await waitFor(() => expect(screen.getByTestId('cmp-aggregate')).toHaveTextContent('54%'))
  })

  it('renders nothing when the comparators are unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    const { container } = render(<NightWidebodies />)
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('says the ratio is not a per-flight multiplier', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    await waitFor(() => expect(screen.getByTestId('cmp-caveat')).toHaveTextContent(/not a per-flight multiplier/i))
  })

  it('survives a network error rather than throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const { container } = render(<NightWidebodies />)
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })
})
