import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Segment } from '../../lib/track'
import SegmentBars from './SegmentBars'

const segs = (efs: number[]): Segment[] =>
  efs.map((efJ, index) => ({ index, efJ, efShare: 0, lon: index, lat: index, altM: 11000 }))

describe('SegmentBars', () => {
  it('draws one bar per segment', () => {
    render(<SegmentBars segments={segs([0, 0, 5e13, 0])} active={0} peak={2} />)
    // ^seg-bar$|-peak|-active — must not also match the seg-bars-alt paragraph.
    expect(screen.getAllByTestId(/^seg-bar(-peak|-active)?$/)).toHaveLength(4)
  })

  it('marks the peak segment', () => {
    render(<SegmentBars segments={segs([0, 5e13, 0])} active={0} peak={1} />)
    expect(screen.getByTestId('seg-bar-peak')).toBeInTheDocument()
  })

  it('marks the active segment separately from the peak', () => {
    render(<SegmentBars segments={segs([0, 5e13, 0])} active={2} peak={1} />)
    expect(screen.getByTestId('seg-bar-active')).toBeInTheDocument()
    expect(screen.getByTestId('seg-bar-peak')).toBeInTheDocument()
  })

  it('carries a text equivalent naming the concentration', () => {
    render(<SegmentBars segments={segs([0, 0, 5e13, 0, 0])} active={0} peak={2} />)
    expect(screen.getByTestId('seg-bars-alt')).toHaveTextContent(/1 of 5/)
  })

  it('renders a cooling segment in the cool colour', () => {
    render(<SegmentBars segments={segs([0, -5e13, 0])} active={0} peak={1} />)
    expect(screen.getByTestId('seg-bar-peak')).toHaveAttribute('fill', 'var(--cool)')
  })

  it('renders nothing rather than crashing on an empty track', () => {
    const { container } = render(<SegmentBars segments={[]} active={0} peak={-1} />)
    expect(container.querySelectorAll('[data-testid^="seg-bar"]')).toHaveLength(0)
  })
})
