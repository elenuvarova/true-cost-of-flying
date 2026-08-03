import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OwnerAgg } from '../lib/data'
import Leaderboard from './Leaderboard'

const owner = (o: Partial<OwnerAgg> & { owner: string }): OwnerAgg => ({
  ac_type: 'Boeing 757-200',
  flights: 7,
  fuelT: 0,
  contrailT: 0,
  combinedT: 0,
  warm: 0,
  cool: 0,
  zero: 0,
  bizjet: false,
  proxy: false,
  tier: 'med',
  ...o,
})

const OWNERS: OwnerAgg[] = [
  owner({ owner: 'Alpha', fuelT: 300, contrailT: 5, combinedT: 305 }),
  owner({ owner: 'Bravo', fuelT: 100, contrailT: 150, combinedT: 250 }),
  owner({ owner: 'Charlie', fuelT: 280, contrailT: -60, combinedT: 220 }),
]

const names = () => screen.getAllByTestId('lb-name').map((el) => el.textContent)

const setup = () =>
  render(<Leaderboard owners={OWNERS} total={84} horizon="GWP100" onHorizon={vi.fn()} />)

describe('Leaderboard', () => {
  it('opens ranked by combined CO₂e', () => {
    setup()
    expect(names()).toEqual(['Alpha', 'Bravo', 'Charlie'])
  })

  it('reorders when the metric switches to fuel', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    expect(names()).toEqual(['Alpha', 'Charlie', 'Bravo'])
  })

  it('marks the active metric with aria-pressed', async () => {
    setup()
    const fuel = screen.getByRole('button', { name: /Fuel CO₂/ })
    expect(fuel).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(fuel)
    expect(fuel).toHaveAttribute('aria-pressed', 'true')
  })

  it('states how many owners moved', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    expect(screen.getByTestId('reshuffle-note')).toHaveTextContent(/2 of 3/)
    expect(screen.getByTestId('reshuffle-note')).toHaveTextContent(/Bravo/)
  })

  it('announces the new order to screen readers', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    const live = screen.getByTestId('lb-live')
    expect(live).toHaveAttribute('aria-live', 'polite')
    expect(live).toHaveTextContent(/Alpha/)
  })

  it('renders the horizon toggle in this section', () => {
    setup()
    expect(within(screen.getByRole('group', { name: /Time horizon/ })).getByText('GWP20')).toBeInTheDocument()
  })

  it('shows a signed value on the contrails-only metric', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Contrails only/ }))
    // Charlie net-cools, so it sinks to last and reads as a negative.
    expect(names()).toEqual(['Bravo', 'Alpha', 'Charlie'])
    expect(screen.getByTestId('lb-live')).toHaveTextContent(/Contrails only/)
  })
})
