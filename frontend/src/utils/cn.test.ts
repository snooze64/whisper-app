/**
 * cn (className merge) utility tests
 */
import { describe, it, expect } from 'vitest'
import { cn } from './cn'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2')
  })

  it('handles conditional classes', () => {
    expect(cn('class1', false && 'class2', 'class3')).toBe('class1 class3')
    expect(cn('class1', true && 'class2')).toBe('class1 class2')
  })

  it('handles Tailwind class conflicts', () => {
    // twMerge should keep the last class when there's a conflict
    expect(cn('p-4', 'p-8')).toBe('p-8')
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
  })

  it('handles arrays of classes', () => {
    expect(cn(['class1', 'class2'])).toBe('class1 class2')
  })

  it('handles objects of classes', () => {
    expect(cn({ class1: true, class2: false, class3: true })).toBe('class1 class3')
  })

  it('handles mixed inputs', () => {
    expect(
      cn(
        'base-class',
        { conditional: true },
        ['array-class1', 'array-class2'],
        false && 'ignored-class'
      )
    ).toBe('base-class conditional array-class1 array-class2')
  })

  it('handles undefined and null', () => {
    expect(cn('class1', undefined, null, 'class2')).toBe('class1 class2')
  })

  it('handles duplicate classes', () => {
    // clsx doesn't remove duplicates, that's expected behavior
    const result = cn('class1', 'class1', 'class2')
    expect(result).toContain('class1')
    expect(result).toContain('class2')
  })
})
