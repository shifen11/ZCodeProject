export interface SubtitleLine {
  text: string;
  isFinal: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
