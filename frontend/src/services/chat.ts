import type { ChatRequest, StreamEvent, ChatSession, ChatMessage } from '../types';
import api from './api';
import { getAuthToken, refreshAccessToken } from './auth';

/** SSE fetch with automatic token refresh on 401. */
async function sseFetchWithRefresh(
  url: string,
  body: Record<string, unknown>,
  signal: AbortSignal,
): Promise<Response> {
  const doFetch = (token: string | null) =>
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token || ''}`,
      },
      body: JSON.stringify(body),
      signal,
    });

  let response = await doFetch(getAuthToken());

  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      response = await doFetch(newToken);
    }
  }

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
    } catch (e) {
      if (e instanceof Error && e.message !== `HTTP error! status: ${response.status}`) throw e;
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  return response;
}

/** Read SSE stream and dispatch events. */
async function readSSEStream(
  response: Response,
  onMessage: (event: StreamEvent) => void,
  onComplete: () => void,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) { onComplete(); break; }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') { onComplete(); return; }
        try { onMessage(JSON.parse(data)); } catch { /* incomplete */ }
      }
    }
  }
}

export const chatService = {
  // Stream chat messages using SSE
  streamChat(
    request: ChatRequest,
    onMessage: (event: StreamEvent) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): () => void {
    const controller = new AbortController();

    sseFetchWithRefresh(
      '/api/chat/stream',
      {
        agent_id: request.agentId,
        message: request.message,
        session_id: request.sessionId,
        enable_skills: request.enableSkills,
        enable_mcp: request.enableMCP,
      },
      controller.signal,
    )
      .then((response) => readSSEStream(response, onMessage, onComplete))
      .catch((error) => {
        if (error.name !== 'AbortError') onError(error);
      });

    return () => { controller.abort(); };
  },

  // List chat sessions
  async listSessions(agentId?: string): Promise<ChatSession[]> {
    const params = agentId ? { agent_id: agentId } : {};
    const response = await api.get<ChatSession[]>('/chat/sessions', { params });
    return response.data;
  },

  // Get a specific session
  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await api.get<ChatSession>(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  // Get messages for a session
  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const response = await api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
    return response.data;
  },

  // Delete chat session
  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  // Stop a running chat session
  async stopSession(sessionId: string): Promise<{ status: string; message: string }> {
    const response = await api.post<{ status: string; message: string }>(`/chat/stop/${sessionId}`);
    return response.data;
  },

  // Submit AskUserQuestion answer and continue streaming
  streamAnswerQuestion(
    request: {
      agentId: string;
      sessionId: string;
      toolUseId: string;
      answers: Record<string, string>;
      enableSkills?: boolean;
      enableMCP?: boolean;
    },
    onMessage: (event: StreamEvent) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ): () => void {
    const controller = new AbortController();

    sseFetchWithRefresh(
      '/api/chat/answer-question',
      {
        agent_id: request.agentId,
        session_id: request.sessionId,
        tool_use_id: request.toolUseId,
        answers: request.answers,
        enable_skills: request.enableSkills,
        enable_mcp: request.enableMCP,
      },
      controller.signal,
    )
      .then((response) => readSSEStream(response, onMessage, onComplete))
      .catch((error) => {
        if (error.name !== 'AbortError') onError(error);
      });

    return () => { controller.abort(); };
  },
};
