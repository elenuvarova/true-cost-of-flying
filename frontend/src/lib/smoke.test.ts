import { describe, expect, it } from 'vitest'
import { tonnes } from './data'

describe('test harness', () => {
  it('runs and can import the data layer', () => {
    expect(tonnes(1234)).toBe('1.2')
  })
})
