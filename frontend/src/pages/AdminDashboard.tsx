/**
 * Admin Dashboard page
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { adminAPI } from '@/services/api'
import { DashboardStats, SystemStatus } from '@/types/admin'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import HourlyStatsChart from '@/components/HourlyStatsChart'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  useEffect(() => {
    if (!user?.is_admin) {
      navigate('/')
      return
    }
    loadData()
    // Refresh data every 30 seconds
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [user])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, statusData] = await Promise.all([
        adminAPI.getDashboardStats(),
        adminAPI.getSystemStatus(),
      ])
      setStats(statsData)
      setSystemStatus(statusData)
      setError(null)
    } catch (err) {
      setError('データの読み込みに失敗しました')
      console.error('Failed to load admin data:', err)
    } finally {
      setLoading(false)
    }
  }

  if (!user?.is_admin) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold cursor-pointer" onClick={() => navigate('/')}>
            Whisper Transcription
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.username}
              <span className="ml-2 text-primary">(管理者)</span>
            </span>
            <Button onClick={handleLogout} variant="outline" size="sm">
              ログアウト
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold mb-2">管理者ダッシュボード</h2>
            <p className="text-muted-foreground">システムの利用状況と統計情報</p>
          </div>
          <Button onClick={loadData} variant="outline" size="sm" disabled={loading}>
            {loading ? '更新中...' : '更新'}
          </Button>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && !stats ? (
          <div className="text-center py-12">データを読み込み中...</div>
        ) : (
          <>
            {/* System Status */}
            {systemStatus && (
              <div className="mb-6">
                <h3 className="text-xl font-semibold mb-4">システムステータス</h3>
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">GPU</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2">
                        <Badge variant={systemStatus.gpu_available ? 'default' : 'secondary'}>
                          {systemStatus.gpu_available ? '利用可能' : '利用不可'}
                        </Badge>
                      </div>
                      {systemStatus.gpu_available && systemStatus.gpu_memory_total && (
                        <div className="mt-2 text-sm text-muted-foreground">
                          <div>使用: {systemStatus.gpu_memory_used} MB</div>
                          <div>空き: {systemStatus.gpu_memory_free} MB</div>
                          <div>使用率: {systemStatus.gpu_utilization?.toFixed(1)}%</div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">ワーカー</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{systemStatus.active_workers}</div>
                      <p className="text-xs text-muted-foreground">アクティブなワーカー</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">待機中</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{systemStatus.pending_tasks}</div>
                      <p className="text-xs text-muted-foreground">キュー内のタスク</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">処理中</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{systemStatus.processing_tasks}</div>
                      <p className="text-xs text-muted-foreground">実行中のタスク</p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {/* Overall Statistics */}
            {stats && (
              <>
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-4">全体統計</h3>
                  <div className="grid gap-4 md:grid-cols-3">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">総ユーザー数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{stats.total_users}</div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">総タスク数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">{stats.total_tasks}</div>
                        <p className="text-xs text-muted-foreground">
                          実行中: {stats.active_tasks}
                        </p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">本日の平均処理時間</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">
                          {stats.avg_processing_time_today.toFixed(1)}s
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-4">本日の処理状況</h3>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">完了タスク</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                          {stats.completed_tasks_today}
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">失敗タスク</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-red-600">
                          {stats.failed_tasks_today}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {/* Model Usage */}
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-4">モデル使用状況</h3>
                  <Card>
                    <CardContent className="pt-6">
                      {Object.keys(stats.model_usage).length > 0 ? (
                        <div className="grid gap-2">
                          {Object.entries(stats.model_usage).map(([model, count]) => (
                            <div key={model} className="flex items-center justify-between">
                              <span className="font-medium">{model}</span>
                              <Badge>{count} 回</Badge>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-center text-muted-foreground">データがありません</p>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Format Usage */}
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-4">ファイル形式別使用状況</h3>
                  <Card>
                    <CardContent className="pt-6">
                      {Object.keys(stats.format_usage).length > 0 ? (
                        <div className="grid gap-2">
                          {Object.entries(stats.format_usage).map(([format, count]) => (
                            <div key={format} className="flex items-center justify-between">
                              <span className="font-medium">{format.toUpperCase()}</span>
                              <Badge>{count} 回</Badge>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-center text-muted-foreground">データがありません</p>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Hourly Stats */}
                {stats.hourly_stats.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold mb-4">時間別処理状況（過去24時間）</h3>
                    <Card>
                      <CardContent className="pt-6">
                        <HourlyStatsChart hourlyStats={stats.hourly_stats} />
                      </CardContent>
                    </Card>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
