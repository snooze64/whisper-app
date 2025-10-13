/**
 * API client tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock axios with inline functions
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  }

  return {
    default: {
      create: vi.fn(() => mockInstance),
      post: vi.fn(),
      get: vi.fn(),
    },
    __mockInstance: mockInstance, // Export for test access
  }
})

// Import axios to get mock instance
import axios from 'axios'
// @ts-ignore - accessing mock instance
const mockAxios = axios.create()

// NOW import the API modules
import { authAPI, transcriptionAPI } from './api'

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

describe('authAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  it('login sends credentials and returns tokens', async () => {
    const mockResponse = {
      data: {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
      },
    }

    vi.mocked(mockAxios.post).mockResolvedValueOnce(mockResponse)

    const result = await authAPI.login({
      username: 'testuser',
      password: 'password123',
    })

    expect(mockAxios.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      username: 'testuser',
      password: 'password123',
    })
    expect(result).toEqual(mockResponse.data)
  })

  it('getCurrentUser returns current user info', async () => {
    const mockResponse = {
      data: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        is_admin: false,
        created_at: '2025-01-01T00:00:00Z',
        last_login: '2025-01-01T00:00:00Z',
      },
    }

    vi.mocked(mockAxios.get).mockResolvedValueOnce(mockResponse)

    const result = await authAPI.getCurrentUser()

    expect(mockAxios.get).toHaveBeenCalledWith('/api/v1/auth/me')
    expect(result).toEqual(mockResponse.data)
  })

  it('logout calls logout endpoint', async () => {
    vi.mocked(mockAxios.post).mockResolvedValueOnce({ data: {} })

    await authAPI.logout()

    expect(mockAxios.post).toHaveBeenCalledWith('/api/v1/auth/logout')
  })

  it('refreshToken sends refresh token and returns new tokens', async () => {
    const mockResponse = {
      data: {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
      },
    }

    vi.mocked(mockAxios.post).mockResolvedValueOnce(mockResponse)

    const result = await authAPI.refreshToken('old-refresh-token')

    expect(mockAxios.post).toHaveBeenCalledWith('/api/v1/auth/refresh', {
      refresh_token: 'old-refresh-token',
    })
    expect(result).toEqual(mockResponse.data)
  })
})

describe('transcriptionAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getTranscription fetches transcription by task ID', async () => {
    const mockResponse = {
      data: {
        id: 1,
        task_id: '123',
        transcription_text: 'Test transcription',
        segments: [],
        word_count: 2,
        subtitle_path: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    }

    vi.mocked(mockAxios.get).mockResolvedValueOnce(mockResponse)

    const result = await transcriptionAPI.getTranscription('123')

    expect(mockAxios.get).toHaveBeenCalledWith('/api/v1/tasks/123/transcription')
    expect(result).toEqual(mockResponse.data)
  })

  it('updateTranscription updates full transcription', async () => {
    const mockResponse = {
      data: {
        id: 1,
        task_id: '123',
        transcription_text: 'Updated transcription',
        segments: [
          { id: 0, text: 'Updated segment', start: 0, end: 5 },
        ],
        word_count: 2,
        subtitle_path: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    }

    const updateData = {
      transcription_text: 'Updated transcription',
      segments: [
        { id: 0, text: 'Updated segment', start: 0, end: 5 },
      ],
    }

    vi.mocked(mockAxios.put).mockResolvedValueOnce(mockResponse)

    const result = await transcriptionAPI.updateTranscription('123', updateData)

    expect(mockAxios.put).toHaveBeenCalledWith(
      '/api/v1/tasks/123/transcription',
      updateData
    )
    expect(result).toEqual(mockResponse.data)
  })

  it('updateSegment updates a single segment', async () => {
    const mockResponse = {
      data: {
        id: 1,
        task_id: '123',
        transcription_text: 'Updated text',
        segments: [
          { id: 0, text: 'Updated segment', start: 0, end: 5 },
        ],
        word_count: 2,
        subtitle_path: null,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      },
    }

    const updateData = {
      segment_id: 0,
      text: 'Updated segment',
      start: 0,
      end: 5,
    }

    vi.mocked(mockAxios.patch).mockResolvedValueOnce(mockResponse)

    const result = await transcriptionAPI.updateSegment('123', updateData)

    expect(mockAxios.patch).toHaveBeenCalledWith(
      '/api/v1/tasks/123/transcription/segments',
      updateData
    )
    expect(result).toEqual(mockResponse.data)
  })

  it('downloadSubtitle returns blob', async () => {
    const mockBlob = new Blob(['subtitle content'], { type: 'text/plain' })
    const mockResponse = { data: mockBlob }

    vi.mocked(mockAxios.get).mockResolvedValueOnce(mockResponse)

    const result = await transcriptionAPI.downloadSubtitle('123', 'srt')

    expect(mockAxios.get).toHaveBeenCalledWith(
      '/api/v1/tasks/123/subtitle',
      expect.objectContaining({
        params: { format: 'srt' },
        responseType: 'blob',
      })
    )
    expect(result).toBe(mockBlob)
  })

  it('downloadText returns blob', async () => {
    const mockBlob = new Blob(['text content'], { type: 'text/plain' })
    const mockResponse = { data: mockBlob }

    vi.mocked(mockAxios.get).mockResolvedValueOnce(mockResponse)

    const result = await transcriptionAPI.downloadText('123')

    expect(mockAxios.get).toHaveBeenCalledWith(
      '/api/v1/tasks/123/text',
      expect.objectContaining({
        responseType: 'blob',
      })
    )
    expect(result).toBe(mockBlob)
  })
})
