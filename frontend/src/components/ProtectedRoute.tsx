/**
 * Protected Route component
 * Redirects to login if user is not authenticated
 */
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export default function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requireAdmin && !user?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold">アクセス拒否</h1>
          <p className="text-muted-foreground mt-2">
            このページにアクセスするには管理者権限が必要です
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
