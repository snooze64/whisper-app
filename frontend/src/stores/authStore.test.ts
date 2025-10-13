/**
 * Auth store tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from './authStore'
import { authAPI } from '@/services/api'
import type { User } from '@/types/auth'

// Mock the API
vi.mock('@/services/api', () => ({
  authAPI: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    // Clear all mocks
    vi.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  it('initializes with null user and no authentication', () => {
    const { user, accessToken, refreshToken, isAuthenticated } = useAuthStore.getState()

    expect(user).toBeNull()
    expect(accessToken).toBeNull()
    expect(refreshToken).toBeNull()
    expect(isAuthenticated).toBe(false)
  })

  it('login updates user and tokens on success', async () => {
    const mockUser: User = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      is_admin: false,
      created_at: '2025-01-01T00:00:00Z',
      last_login: '2025-01-01T00:00:00Z',
    }
    const mockTokens = {
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      token_type: 'bearer',
    }

    vi.mocked(authAPI.login).mockResolvedValueOnce(mockTokens)
    vi.mocked(authAPI.getCurrentUser).mockResolvedValueOnce(mockUser)

    await useAuthStore.getState().login('testuser', 'password')

    const { user, accessToken, refreshToken, isAuthenticated, isLoading, error } = useAuthStore.getState()

    expect(user).toEqual(mockUser)
    expect(accessToken).toBe('test-access-token')
    expect(refreshToken).toBe('test-refresh-token')
    expect(isAuthenticated).toBe(true)
    expect(isLoading).toBe(false)
    expect(error).toBeNull()
    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'test-access-token')
    expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'test-refresh-token')
  })

  it('login sets error on failure', async () => {
    const mockError = {
      response: {
        data: {
          detail: 'Invalid credentials',
        },
      },
    }

    vi.mocked(authAPI.login).mockRejectedValueOnce(mockError)

    await expect(useAuthStore.getState().login('testuser', 'wrongpassword')).rejects.toThrow()

    const { user, accessToken, isAuthenticated, isLoading, error } = useAuthStore.getState()

    expect(user).toBeNull()
    expect(accessToken).toBeNull()
    expect(isAuthenticated).toBe(false)
    expect(isLoading).toBe(false)
    expect(error).toBe('Invalid credentials')
  })

  it('logout clears state and tokens', () => {
    // First set authentication state
    useAuthStore.setState({
      user: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_admin: false,
        created_at: '2025-01-01T00:00:00Z',
        last_login: '2025-01-01T00:00:00Z',
      },
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      isAuthenticated: true,
    })

    vi.mocked(authAPI.logout).mockResolvedValueOnce()

    useAuthStore.getState().logout()

    const { user, accessToken, refreshToken, isAuthenticated } = useAuthStore.getState()

    expect(user).toBeNull()
    expect(accessToken).toBeNull()
    expect(refreshToken).toBeNull()
    expect(isAuthenticated).toBe(false)
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token')
  })

  it('setUser updates only user data', () => {
    const initialUser: User = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      is_admin: false,
      created_at: '2025-01-01T00:00:00Z',
      last_login: '2025-01-01T00:00:00Z',
    }
    useAuthStore.setState({
      user: initialUser,
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      isAuthenticated: true,
    })

    const updatedUser: User = {
      ...initialUser,
      email: 'updated@example.com',
      last_login: '2025-01-02T00:00:00Z',
    }
    useAuthStore.getState().setUser(updatedUser)

    const { user, accessToken, isAuthenticated } = useAuthStore.getState()

    expect(user).toEqual(updatedUser)
    expect(accessToken).toBe('test-token') // Token should remain unchanged
    expect(isAuthenticated).toBe(true)
  })

  it('handles admin user correctly', () => {
    const adminUser: User = {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      is_admin: true,
      created_at: '2025-01-01T00:00:00Z',
      last_login: '2025-01-01T00:00:00Z',
    }

    useAuthStore.setState({
      user: adminUser,
      accessToken: 'admin-token',
      refreshToken: 'admin-refresh',
      isAuthenticated: true,
    })

    const { user } = useAuthStore.getState()

    expect(user?.is_admin).toBe(true)
  })

  it('refreshAccessToken updates tokens', async () => {
    useAuthStore.setState({
      refreshToken: 'old-refresh-token',
    })

    const mockTokens = {
      access_token: 'new-access-token',
      refresh_token: 'new-refresh-token',
      token_type: 'bearer',
    }

    vi.mocked(authAPI.refreshToken).mockResolvedValueOnce(mockTokens)

    await useAuthStore.getState().refreshAccessToken()

    const { accessToken, refreshToken } = useAuthStore.getState()

    expect(accessToken).toBe('new-access-token')
    expect(refreshToken).toBe('new-refresh-token')
    expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new-access-token')
    expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'new-refresh-token')
  })

  it('clearError clears error message', () => {
    useAuthStore.setState({
      error: 'Some error message',
    })

    useAuthStore.getState().clearError()

    const { error } = useAuthStore.getState()

    expect(error).toBeNull()
  })
})
