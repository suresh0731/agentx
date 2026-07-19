import type { ExceptionSummary, InstructionSummary, WorkbenchCard } from './api-client.js';

export interface WsMessage {
  type: string;
  id: string;
  instruction?: InstructionSummary;
  workbench?: WorkbenchCard;
  exception?: ExceptionSummary;
}

type Handler = (data: WsMessage) => void;
type ConnectHandler = () => void;

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers: Handler[] = [];
  private connectHandlers: ConnectHandler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;

  get connected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/api/v1/ws/ops`);

    this.ws.onopen = () => {
      this.connectHandlers.forEach((h) => h());
    };

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsMessage;
        this.handlers.forEach((h) => h(data));
        document.dispatchEvent(new CustomEvent('ax-ws', { detail: data }));
      } catch { /* ignore malformed payloads */ }
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (!this.shouldReconnect) return;
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  on(handler: Handler) {
    this.handlers.push(handler);
  }

  off(handler: Handler) {
    this.handlers = this.handlers.filter((h) => h !== handler);
  }

  onConnect(handler: ConnectHandler) {
    this.connectHandlers.push(handler);
    if (this.connected) handler();
  }

  offConnect(handler: ConnectHandler) {
    this.connectHandlers = this.connectHandlers.filter((h) => h !== handler);
  }
}

export const wsClient = new WsClient();
