import { useState, useEffect, useCallback, useRef } from 'react';
import { API_ENDPOINTS, STORAGE_KEYS } from '../constants';

export interface SSELog {
  timestamp: string;
  type: 'node' | 'tool' | 'token' | 'system' | 'error';
  message: string;
  nodeName?: string;
  toolName?: string;
}

export interface PendingInterrupt {
  id: string;
  ticker: string;
}

export interface SSEState {
  logs: SSELog[];
  activeNode: string | null;
  activeTool: string | null;
  streamedText: string;
  isStreaming: boolean;
  error: string | null;
  isCompleted: boolean;
  pendingInterrupts: PendingInterrupt[];
}

const initialSSEState: SSEState = {
  logs: [],
  activeNode: null,
  activeTool: null,
  streamedText: '',
  isStreaming: false,
  error: null,
  isCompleted: false,
  pendingInterrupts: [],
};

export function useSSE(threadId: string | null) {
  const [state, setState] = useState<SSEState>(initialSSEState);
  const eventSourceRef = useRef<EventSource | null>(null);

  const resetStreamState = useCallback(() => {
    setState(initialSSEState);
  }, []);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setState((prev) => ({ ...prev, isStreaming: false }));
    }
  }, []);

  const connect = useCallback(() => {
    if (!threadId) return;

    disconnect();
    resetStreamState();

    setState((prev) => ({ ...prev, isStreaming: true }));

    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
    const url = `${API_ENDPOINTS.STREAM_RESEARCH(threadId)}${tokenQuery}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    const addLog = (type: SSELog['type'], message: string, nodeName?: string, toolName?: string) => {
      const newLog: SSELog = {
        timestamp: new Date().toLocaleTimeString(),
        type,
        message,
        nodeName,
        toolName,
      };
      setState((prev) => ({
        ...prev,
        logs: [...prev.logs, newLog],
      }));
    };

    eventSource.onopen = () => {
      addLog('system', 'Connection established with analysis engine.');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.event;

        switch (eventType) {
          case 'node_start':
            const node = data.node;
            setState((prev) => ({ ...prev, activeNode: node, activeTool: null }));
            addLog('node', `Supervisor routed execution to Node: ${node}`, node);
            break;

          case 'tool_start':
            const tool = data.tool;
            const inputStr = data.input ? ` (input: ${JSON.stringify(data.input)})` : '';
            setState((prev) => ({ ...prev, activeTool: tool }));
            addLog('tool', `Running tool: ${tool}${inputStr}`, undefined, tool);
            break;

          case 'token':
            const text = data.text;
            setState((prev) => ({
              ...prev,
              streamedText: prev.streamedText + text,
            }));
            break;

          case 'completed':
            setState((prev) => ({
              ...prev,
              isStreaming: false,
              isCompleted: true,
              activeNode: null,
              activeTool: null,
            }));
            addLog('system', 'Research completed successfully. Brief published.');
            disconnect();
            break;

          case 'interrupt':
            const interrupts = data.interrupts || [];
            // Parse interrupts into friendly pending structure
            const pending = interrupts.map((i: any) => ({
              id: i.id,
              ticker: i.value,
            }));
            setState((prev) => ({
              ...prev,
              isStreaming: false,
              activeNode: 'await_human_review',
              activeTool: null,
              pendingInterrupts: pending,
            }));
            addLog('system', `Factual Synthesis Intercepted: Awaiting Analyst approval.`);
            disconnect();
            break;

          case 'error':
            const errMsg = data.message || 'Unknown server error.';
            setState((prev) => ({
              ...prev,
              isStreaming: false,
              error: errMsg,
              activeNode: null,
              activeTool: null,
            }));
            addLog('error', `Agent execution failed: ${errMsg}`);
            disconnect();
            break;

          default:
            // Generic message catch
            break;
        }
      } catch (err) {
        console.error('Error parsing SSE event data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource connection error:', err);
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        error: 'Lost connection to streaming service.',
      }));
      addLog('error', 'Lost connection to backend event stream.');
      disconnect();
    };
  }, [threadId, disconnect, resetStreamState]);

  useEffect(() => {
    if (threadId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [threadId, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    resetStreamState,
  };
}
