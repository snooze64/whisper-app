import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload as UploadIcon, FileAudio, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '@/services/api';

const ALLOWED_FORMATS = ['mp3', 'wav', 'mp4'];
const MAX_FILE_SIZE = 1024 * 1024 * 1024; // 1GB

export default function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<string>('tiny');
  const [language, setLanguage] = useState<string>('ja');
  const [numSpeakers, setNumSpeakers] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'video/mp4': ['.mp4'],
    },
    maxSize: MAX_FILE_SIZE,
    maxFiles: 1,
    onDrop: (acceptedFiles, rejectedFiles) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('ファイルサイズが1GBを超えています');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError(`対応していないファイル形式です。対応形式: ${ALLOWED_FORMATS.join(', ')}`);
        } else {
          setError('ファイルのアップロードに失敗しました');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0]);
      }
    },
  });

  const handleUpload = async () => {
    if (!file) {
      setError('ファイルを選択してください');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', model);
      formData.append('language', language);
      if (numSpeakers) {
        formData.append('num_speakers', numSpeakers);
      }

      const response = await api.post('/api/v1/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Navigate to task detail page
      navigate(`/tasks/${response.data.id}`);
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'アップロードに失敗しました');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">ファイルアップロード</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>音声・動画ファイル</CardTitle>
          <CardDescription>
            文字起こしを行う音声または動画ファイルをアップロードしてください
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-primary bg-primary/5'
                : 'border-gray-300 hover:border-primary'
            }`}
          >
            <input {...getInputProps()} />
            <UploadIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            {isDragActive ? (
              <p className="text-lg">ファイルをドロップしてください...</p>
            ) : (
              <div>
                <p className="text-lg mb-2">
                  ファイルをドラッグ&ドロップ、またはクリックして選択
                </p>
                <p className="text-sm text-gray-500">
                  対応形式: MP3, WAV, MP4 (最大 1GB)
                </p>
              </div>
            )}
          </div>

          {file && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg flex items-center gap-3">
              <FileAudio className="h-8 w-8 text-primary" />
              <div className="flex-1">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFile(null)}
              >
                削除
              </Button>
            </div>
          )}

          {error && (
            <Alert variant="destructive" className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>文字起こし設定</CardTitle>
          <CardDescription>
            使用するモデルと言語を選択してください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Whisperモデル</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger id="model">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tiny">Tiny (最速・開発用)</SelectItem>
                <SelectItem value="large-v3-turbo">Large V3 Turbo (高速)</SelectItem>
                <SelectItem value="large-v3">Large V3 (高精度)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-gray-500">
              Turboモデルは高速ですが、精度がやや低下します
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="language">言語</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger id="language">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ja">日本語</SelectItem>
                <SelectItem value="en">英語</SelectItem>
                <SelectItem value="zh">中国語</SelectItem>
                <SelectItem value="ko">韓国語</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="num-speakers">話者数 (オプション)</Label>
            <Input
              id="num-speakers"
              type="number"
              min="1"
              max="10"
              placeholder="自動検出"
              value={numSpeakers}
              onChange={(e) => setNumSpeakers(e.target.value)}
            />
            <p className="text-sm text-gray-500">
              話者数がわかっている場合は入力してください（1-10人）
            </p>
          </div>

          <Button
            className="w-full"
            size="lg"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                アップロード中...
              </>
            ) : (
              <>
                <UploadIcon className="mr-2 h-4 w-4" />
                アップロード開始
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
