/**
 * Transcription types
 */

export interface TranscriptionSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker_id?: number | null;
  speaker_label?: string | null;
  confidence?: number | null;
  avg_logprob?: number | null;
  no_speech_prob?: number | null;
  words?: Array<{
    word: string;
    start: number;
    end: number;
    probability: number;
  }>;
}

export interface Transcription {
  id: number;
  task_id: string;
  transcription_text: string;
  segments: TranscriptionSegment[];
  subtitle_path: string | null;
  word_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface TranscriptionUpdate {
  transcription_text?: string;
  segments?: TranscriptionSegment[];
  word_count?: number;
}

export interface SegmentUpdateRequest {
  segment_id: number;
  text?: string;
  start?: number;
  end?: number;
  speaker_label?: string;
}
