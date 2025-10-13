/**
 * Processing history types
 */

export interface ProcessingHistory {
  id: number
  task_id: string
  user_id: number
  processing_time_seconds: number
  gpu_memory_used_mb: number | null
  model_name: string
  file_format: string
  file_size_mb: number
  success: boolean
  error_type: string | null
  created_at: string
}

export interface ProcessingHistoryListResponse {
  history: ProcessingHistory[]
  total: number
  page: number
  page_size: number
}

export interface ProcessingHistoryStats {
  total_tasks: number
  successful_tasks: number
  failed_tasks: number
  success_rate: number
  avg_processing_time: number
  total_processing_time: number
  avg_gpu_memory: number | null
  total_file_size: number
}

export interface HistoryListParams {
  page?: number
  page_size?: number
  success?: boolean
  model_name?: string
}
