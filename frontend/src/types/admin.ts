/**
 * Admin types
 */

export interface HourlyStats {
  hour: string
  total: number
  successful: number
  failed: number
}

export interface DashboardStats {
  total_users: number
  total_tasks: number
  active_tasks: number
  completed_tasks_today: number
  failed_tasks_today: number
  avg_processing_time_today: number
  model_usage: Record<string, number>
  format_usage: Record<string, number>
  hourly_stats: HourlyStats[]
}

export interface SystemStatus {
  gpu_available: boolean
  gpu_memory_total: number | null
  gpu_memory_used: number | null
  gpu_memory_free: number | null
  gpu_utilization: number | null
  active_workers: number
  pending_tasks: number
  processing_tasks: number
}

export interface Task {
  id: string
  user_id: number
  filename: string
  file_path: string
  file_format: string
  file_size: number
  model_name: string
  language: string
  status: string
  progress: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  page: number
  page_size: number
}

export interface UserListResponse {
  users: Array<{
    id: number
    username: string
    email: string | null
    is_admin: boolean
    created_at: string
    last_login: string | null
  }>
  total: number
  page: number
  page_size: number
}

export interface OverallStats {
  total_users: number
  total_tasks: number
  total_completed: number
  total_failed: number
  total_processing_time_hours: number
  avg_processing_time_seconds: number
  total_file_size_gb: number
}

export interface TaskListParams {
  page?: number
  page_size?: number
  status?: string
  user_id?: number
}

export interface UserListParams {
  page?: number
  page_size?: number
}
