import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, FileAudio, Clock, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { api } from '@/services/api';

interface Task {
  id: string;
  filename: string;
  file_size: number;
  file_format: string;
  model_name: string;
  language: string;
  num_speakers: number | null;
  status: string;
  progress: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

const statusConfig = {
  pending: { label: '待機中', color: 'bg-gray-500', icon: Clock },
  processing: { label: '処理中', color: 'bg-blue-500', icon: Loader2 },
  completed: { label: '完了', color: 'bg-green-500', icon: CheckCircle },
  failed: { label: '失敗', color: 'bg-red-500', icon: XCircle },
};

export default function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTask();
    // Poll for status updates every 3 seconds if processing
    const interval = setInterval(() => {
      if (task?.status === 'processing' || task?.status === 'pending') {
        fetchTaskStatus();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId, task?.status]);

  const fetchTask = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/tasks/${taskId}`);
      setTask(response.data);
    } catch (err: any) {
      console.error('Failed to fetch task:', err);
      setError(err.response?.data?.detail || 'タスク情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskStatus = async () => {
    try {
      const response = await api.get(`/api/v1/tasks/${taskId}/status`);
      setTask((prev) => prev ? { ...prev, ...response.data } : null);
    } catch (err) {
      console.error('Failed to fetch task status:', err);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('ja-JP');
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-4xl">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="container mx-auto py-8 px-4 max-w-4xl">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'タスクが見つかりません'}</AlertDescription>
        </Alert>
        <Button className="mt-4" onClick={() => navigate('/')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          ダッシュボードに戻る
        </Button>
      </div>
    );
  }

  const statusInfo = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.pending;
  const StatusIcon = statusInfo.icon;

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      <Button variant="ghost" className="mb-4" asChild>
        <Link to="/">
          <ArrowLeft className="mr-2 h-4 w-4" />
          ダッシュボードに戻る
        </Link>
      </Button>

      <h1 className="text-3xl font-bold mb-8">タスク詳細</h1>

      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileAudio className="h-8 w-8 text-primary" />
              <div>
                <CardTitle>{task.filename}</CardTitle>
                <CardDescription>{formatFileSize(task.file_size)} • {task.file_format.toUpperCase()}</CardDescription>
              </div>
            </div>
            <Badge className={statusInfo.color}>
              <StatusIcon className={`mr-1 h-3 w-3 ${task.status === 'processing' ? 'animate-spin' : ''}`} />
              {statusInfo.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {(task.status === 'processing' || task.status === 'pending') && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>処理進行状況</span>
                <span className="font-medium">{task.progress}%</span>
              </div>
              <Progress value={task.progress} />
            </div>
          )}

          {task.error_message && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{task.error_message}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div>
              <p className="text-sm text-gray-500">モデル</p>
              <p className="font-medium">{task.model_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">言語</p>
              <p className="font-medium">{task.language}</p>
            </div>
            {task.num_speakers && (
              <div>
                <p className="text-sm text-gray-500">話者数</p>
                <p className="font-medium">{task.num_speakers}人</p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-500">作成日時</p>
              <p className="font-medium">{formatDate(task.created_at)}</p>
            </div>
            {task.started_at && (
              <div>
                <p className="text-sm text-gray-500">開始日時</p>
                <p className="font-medium">{formatDate(task.started_at)}</p>
              </div>
            )}
            {task.completed_at && (
              <div>
                <p className="text-sm text-gray-500">完了日時</p>
                <p className="font-medium">{formatDate(task.completed_at)}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {task.status === 'completed' && (
        <Card>
          <CardHeader>
            <CardTitle>文字起こし結果</CardTitle>
            <CardDescription>
              文字起こしが完了しました
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-4">
              Phase 4で文字起こし機能を実装後、結果が表示されます
            </p>
            <Button disabled>結果を表示（準備中）</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
