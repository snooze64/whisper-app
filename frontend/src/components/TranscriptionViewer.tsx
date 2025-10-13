import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, Edit2, Save, X, Clock, User, AlertCircle } from 'lucide-react';
import { Transcription, TranscriptionSegment, SegmentUpdateRequest } from '@/types/transcription';
import { transcriptionAPI } from '@/services/api';

interface TranscriptionViewerProps {
  transcription: Transcription;
  taskId: string;
  onUpdate?: (updatedTranscription: Transcription) => void;
}

export default function TranscriptionViewer({ transcription, taskId, onUpdate }: TranscriptionViewerProps) {
  const [editingSegmentId, setEditingSegmentId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<SegmentUpdateRequest | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  const handleEditSegment = (segment: TranscriptionSegment) => {
    setEditingSegmentId(segment.id);
    setEditForm({
      segment_id: segment.id,
      text: segment.text,
      start: segment.start,
      end: segment.end,
      speaker_label: segment.speaker_label || undefined,
    });
    setError(null);
  };

  const handleCancelEdit = () => {
    setEditingSegmentId(null);
    setEditForm(null);
    setError(null);
  };

  const handleSaveSegment = async () => {
    if (!editForm) return;

    try {
      setUpdating(true);
      setError(null);
      const updated = await transcriptionAPI.updateSegment(taskId, editForm);
      if (onUpdate) {
        onUpdate(updated);
      }
      setEditingSegmentId(null);
      setEditForm(null);
    } catch (err: any) {
      console.error('Failed to update segment:', err);
      setError(err.response?.data?.detail || 'セグメントの更新に失敗しました');
    } finally {
      setUpdating(false);
    }
  };

  const handleDownloadSubtitle = async (format: 'srt' | 'vtt') => {
    try {
      setDownloading(true);
      setError(null);
      const blob = await transcriptionAPI.downloadSubtitle(taskId, format);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `transcription_${taskId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to download subtitle:', err);
      setError(err.response?.data?.detail || '字幕ファイルのダウンロードに失敗しました');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadText = async () => {
    try {
      setDownloading(true);
      setError(null);
      const blob = await transcriptionAPI.downloadText(taskId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `transcription_${taskId}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to download text:', err);
      setError(err.response?.data?.detail || 'テキストファイルのダウンロードに失敗しました');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with stats and download buttons */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>文字起こし結果</CardTitle>
              <CardDescription>
                {transcription.segments.length} セグメント • {transcription.word_count || 0} 語
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadText}
                disabled={downloading}
              >
                <Download className="mr-2 h-4 w-4" />
                テキスト
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownloadSubtitle('srt')}
                disabled={downloading}
              >
                <Download className="mr-2 h-4 w-4" />
                SRT
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownloadSubtitle('vtt')}
                disabled={downloading}
              >
                <Download className="mr-2 h-4 w-4" />
                VTT
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Full transcription text */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">全文</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose max-w-none">
            <p className="whitespace-pre-wrap">{transcription.transcription_text}</p>
          </div>
        </CardContent>
      </Card>

      {/* Segments list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">セグメント</CardTitle>
          <CardDescription>
            各セグメントを編集できます
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {transcription.segments.map((segment) => (
              <div
                key={segment.id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                {editingSegmentId === segment.id && editForm ? (
                  // Edit mode
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor={`start-${segment.id}`}>開始時間（秒）</Label>
                        <Input
                          id={`start-${segment.id}`}
                          type="number"
                          step="0.001"
                          value={editForm.start}
                          onChange={(e) =>
                            setEditForm({ ...editForm, start: parseFloat(e.target.value) })
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor={`end-${segment.id}`}>終了時間（秒）</Label>
                        <Input
                          id={`end-${segment.id}`}
                          type="number"
                          step="0.001"
                          value={editForm.end}
                          onChange={(e) =>
                            setEditForm({ ...editForm, end: parseFloat(e.target.value) })
                          }
                        />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor={`speaker-${segment.id}`}>話者ラベル</Label>
                      <Input
                        id={`speaker-${segment.id}`}
                        value={editForm.speaker_label || ''}
                        onChange={(e) =>
                          setEditForm({ ...editForm, speaker_label: e.target.value })
                        }
                        placeholder="Speaker 1"
                      />
                    </div>
                    <div>
                      <Label htmlFor={`text-${segment.id}`}>テキスト</Label>
                      <Textarea
                        id={`text-${segment.id}`}
                        value={editForm.text}
                        onChange={(e) => setEditForm({ ...editForm, text: e.target.value })}
                        rows={4}
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSaveSegment} disabled={updating}>
                        <Save className="mr-2 h-4 w-4" />
                        保存
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCancelEdit}
                        disabled={updating}
                      >
                        <X className="mr-2 h-4 w-4" />
                        キャンセル
                      </Button>
                    </div>
                  </div>
                ) : (
                  // View mode
                  <div>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Clock className="h-4 w-4" />
                        <span>
                          {formatTime(segment.start)} → {formatTime(segment.end)}
                        </span>
                        {segment.speaker_label && (
                          <>
                            <User className="h-4 w-4 ml-2" />
                            <Badge variant="secondary">{segment.speaker_label}</Badge>
                          </>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEditSegment(segment)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-base">{segment.text}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
