/**
 * Dashboard page (protected)
 */
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Dashboard() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Whisper Transcription</h1>
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>ファイルアップロード</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                音声・動画ファイルをアップロードして文字起こしを開始
              </p>
              <Button className="mt-4" onClick={() => navigate('/upload')}>
                アップロード
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>処理履歴</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                過去の文字起こし処理を確認
              </p>
              <Button className="mt-4" variant="outline" onClick={() => navigate('/history')}>
                履歴を見る
              </Button>
            </CardContent>
          </Card>

          {user?.is_admin && (
            <Card>
              <CardHeader>
                <CardTitle>管理者ダッシュボード</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  システム利用状況と統計
                </p>
                <Button className="mt-4" variant="outline" onClick={() => navigate('/admin')}>
                  ダッシュボード
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}
