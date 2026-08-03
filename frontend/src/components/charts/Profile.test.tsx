import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TrackData } from '../../lib/track'
import Profile from './Profile'

const track = (): TrackData => ({
  segments: [
    { index: 0, efJ: 0, efShare: 0, lon: 0, lat: 0, altM: 3000 },
    { index: 1, efJ: 4e13, efShare: 0.5, lon: 1, lat: 1, altM: 12215 },
    { index: 2, efJ: 0, efShare: 0, lon: 2, lat: 2, altM: 9000 },
  ],
  totalAbsEfJ: 4e13,
  peakIndex: 1,
  nonZero: 1,
  maxAltM: 12215,
})

describe('Profile', () => {
  it('opens on the altitude tab and reports the peak flight level', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Altitude/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/FL401/)
  })

  it('switches to the contrail EF tab', async () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /Contrail EF/ }))
    expect(screen.getByRole('button', { name: /Contrail EF/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Altitude/ })).toHaveAttribute('aria-pressed', 'false')
  })

  it('exposes a slider bound to the active segment', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    const slider = screen.getByRole('slider')
    expect(slider).toHaveValue('1')
    expect(slider).toHaveAttribute('aria-valuemax', '2')
  })

  it('calls onActive when the slider moves', () => {
    const onActive = vi.fn()
    render(<Profile track={track()} active={0} onActive={onActive} />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } })
    expect(onActive).toHaveBeenCalledWith(2)
  })

  it('names which profile is on screen', async () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/altitude/)
    await userEvent.click(screen.getByRole('button', { name: /Contrail EF/ }))
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/contrail forcing/)
  })

  it('describes the cursor for screen readers on the slider itself', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    expect(screen.getByRole('slider')).toHaveAttribute(
      'aria-valuetext',
      'Segment 2 of 3, flight level 401',
    )
  })

  it('clamps an out-of-range active index instead of rendering NaN', () => {
    render(<Profile track={track()} active={99} onActive={vi.fn()} />)
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/segment 3 of 3/)
  })

  it('renders nothing for an empty track', () => {
    const empty: TrackData = { segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 }
    const { container } = render(<Profile track={empty} active={0} onActive={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })
})
