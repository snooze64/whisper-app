/**
 * API client with axios
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { TokenResponse, LoginRequest, User } from '@/types/auth'
import { Transcription, TranscriptionUpdate, SegmentUpdateRequest } from '@/types/transcription'
import { ProcessingHistory, ProcessingHistoryListResponse, ProcessingHistoryStats, HistoryListParams } from '@/types/history'
import { DashboardStats, SystemStatus, TaskListResponse, UserListResponse, OverallStats, TaskListParams, UserListParams } from '@/types/admin'

// API base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor for token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post<TokenResponse>(
            `${API_BASE_URL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken }
          )

          const { access_token, refresh_token } = response.data

          // Update tokens
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`
          }
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: async (credentials: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/login', credentials)
    return response.data
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/api/v1/auth/logout')
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/auth/me')
    return response.data
  },
}

// Transcription API
export const transcriptionAPI = {
  getTranscription: async (taskId: string): Promise<Transcription> => {
    const response = await apiClient.get<Transcription>(`/api/v1/tasks/${taskId}/transcription`)
    return response.data
  },

  updateTranscription: async (taskId: string, data: TranscriptionUpdate): Promise<Transcription> => {
    const response = await apiClient.put<Transcription>(`/api/v1/tasks/${taskId}/transcription`, data)
    return response.data
  },

  updateSegment: async (taskId: string, data: SegmentUpdateRequest): Promise<Transcription> => {
    const response = await apiClient.patch<Transcription>(`/api/v1/tasks/${taskId}/transcription/segments`, data)
    return response.data
  },

  downloadSubtitle: async (taskId: string, format: 'srt' | 'vtt'): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/tasks/${taskId}/subtitle`, {
      params: { format },
      responseType: 'blob',
    })
    return response.data
  },

  downloadText: async (taskId: string): Promise<Blob> => {
    const response = await apiClient.get(`/api/v1/tasks/${taskId}/text`, {
      responseType: 'blob',
    })
    return response.data
  },
}

// History API
export const historyAPI = {
  getHistoryList: async (params?: HistoryListParams): Promise<ProcessingHistoryListResponse> => {
    const response = await apiClient.get<ProcessingHistoryListResponse>('/api/v1/history', { params })
    return response.data
  },

  getHistoryDetail: async (historyId: number): Promise<ProcessingHistory> => {
    const response = await apiClient.get<ProcessingHistory>(`/api/v1/history/${historyId}`)
    return response.data
  },

  getMyStats: async (days?: number): Promise<ProcessingHistoryStats> => {
    const response = await apiClient.get<ProcessingHistoryStats>('/api/v1/history/stats/me', {
      params: days ? { days } : undefined,
    })
    return response.data
  },
}

// Admin API
export const adminAPI = {
  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get<DashboardStats>('/api/v1/admin/dashboard')
    return response.data
  },

  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await apiClient.get<SystemStatus>('/api/v1/admin/system-status')
    return response.data
  },

  getAllUsers: async (params?: UserListParams): Promise<UserListResponse> => {
    const response = await apiClient.get<UserListResponse>('/api/v1/admin/users', { params })
    return response.data
  },

  getAllTasks: async (params?: TaskListParams): Promise<TaskListResponse> => {
    const response = await apiClient.get<TaskListResponse>('/api/v1/admin/tasks', { params })
    return response.data
  },

  getOverallStats: async (): Promise<OverallStats> => {
    const response = await apiClient.get<OverallStats>('/api/v1/admin/stats')
    return response.data
  },
}

// Named export for convenience
export const api = apiClient

export default apiClient
