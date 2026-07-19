import type { ExceptionSummary, InstructionSummary, WorkbenchCard } from './api-client.js';

export interface WsMessage {
  type: string;
  id: string;
  instruction?: InstructionSummary;
  workbench?: WorkbenchCard;
  exception?: ExceptionSummary;
}

type Handler = (data: WsMessage) => void;

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers: Handler[] = [];

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/api/v1/ws/ops`);
    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsMessage;
        this.handlers.forEach((h) => h(data));
        document.dispatchEvent(new CustomEvent('ax-ws', { detail: data }));
      } catch { /* ignore */ }
    };
    this.ws.onclose = () => setTimeout(() => this.connect(), 3000);
  }

  on(handler: Handler) {
    this.handlers.push(handler);
  }

  off(handler: Handler) {
    this.handlers = this.handlers.filter((h) => h !== handler);
  }
}

export const wsClient = new WsClient();
