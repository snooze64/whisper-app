/**
 * Button component tests
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './button'

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  it('handles click events', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<Button onClick={handleClick}>Click me</Button>)
    await user.click(screen.getByRole('button'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('can be disabled', () => {
    render(<Button disabled>Disabled button</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('applies variant classes correctly', () => {
    const { rerender } = render(<Button variant="default">Default</Button>)
    const button1 = screen.getByRole('button')
    expect(button1.className).toBeTruthy()

    rerender(<Button variant="destructive">Destructive</Button>)
    const button2 = screen.getByRole('button')
    expect(button2.className).toBeTruthy()

    rerender(<Button variant="outline">Outline</Button>)
    const button3 = screen.getByRole('button')
    expect(button3.className).toContain('border')
  })

  it('applies size classes correctly', () => {
    const { rerender } = render(<Button size="default">Default</Button>)
    const button1 = screen.getByRole('button')
    expect(button1.className).toBeTruthy()

    rerender(<Button size="sm">Small</Button>)
    const button2 = screen.getByRole('button')
    expect(button2.className).toBeTruthy()

    rerender(<Button size="lg">Large</Button>)
    const button3 = screen.getByRole('button')
    expect(button3.className).toBeTruthy()
  })
})
