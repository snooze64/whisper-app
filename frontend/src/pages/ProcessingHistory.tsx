/**
 * Processing History page
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { historyAPI } from '@/services/api'
import { ProcessingHistory, ProcessingHistoryStats } from '@/types/history'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function ProcessingHistoryPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [history, setHistory] = useState<ProcessingHistory[]>([])
  const [stats, setStats] = useState<ProcessingHistoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  useEffect(() => {
    loadHistory()
    loadStats()
  }, [page])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const response = await historyAPI.getHistoryList({ page, page_size: pageSize })
      setHistory(response.history)
      setTotal(response.total)
      setError(null)
    } catch (err) {
      setError('履歴の読み込みに失敗しました')
      console.error('Failed to load history:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const statsData = await historyAPI.getMyStats(30)
      setStats(statsData)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ja-JP')
  }

  const formatFileSize = (mb: number) => {
    return `${mb.toFixed(2)} MB`
  }

  const formatProcessingTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
  }

  const totalPages = Math.ceil(total / pageSize)

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
              {user?.is_admin && <span className="ml-2 text-primary">(管理者)</span>}
            </span>
            <Button onClick={handleLogout} variant="outline" size="sm">
              ログアウト
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold mb-2">処理履歴</h2>
          <p className="text-muted-foreground">過去の文字起こし処理の履歴と統計</p>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid gap-4 md:grid-cols-4 mb-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">合計処理数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_tasks}</div>
                <p className="text-xs text-muted-foreground">過去30日間</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">成功率</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.success_rate.toFixed(1)}%</div>
                <p className="text-xs text-muted-foreground">
                  成功: {stats.successful_tasks} / 失敗: {stats.failed_tasks}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">平均処理時間</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatProcessingTime(Math.round(stats.avg_processing_time))}</div>
                <p className="text-xs text-muted-foreground">ファイルあたり</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">総ファイルサイズ</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{(stats.total_file_size / 1024).toFixed(2)} GB</div>
                <p className="text-xs text-muted-foreground">処理済み</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* History Table */}
        <Card>
          <CardHeader>
            <CardTitle>処理履歴一覧</CardTitle>
            <CardDescription>
              全 {total} 件のうち {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} 件を表示
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {loading ? (
              <div className="text-center py-8">読み込み中...</div>
            ) : history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">履歴がありません</div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日時</TableHead>
                      <TableHead>モデル</TableHead>
                      <TableHead>形式</TableHead>
                      <TableHead>ファイルサイズ</TableHead>
                      <TableHead>処理時間</TableHead>
                      <TableHead>GPU使用量</TableHead>
                      <TableHead>ステータス</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">{formatDate(item.created_at)}</TableCell>
                        <TableCell>{item.model_name}</TableCell>
                        <TableCell>{item.file_format.toUpperCase()}</TableCell>
                        <TableCell>{formatFileSize(item.file_size_mb)}</TableCell>
                        <TableCell>{formatProcessingTime(item.processing_time_seconds)}</TableCell>
                        <TableCell>
                          {item.gpu_memory_used_mb ? `${item.gpu_memory_used_mb} MB` : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={item.success ? 'default' : 'destructive'}>
                            {item.success ? '成功' : '失敗'}
                          </Badge>
                          {item.error_type && (
                            <div className="text-xs text-muted-foreground mt-1">{item.error_type}</div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      前へ
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      ページ {page} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      次へ
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
