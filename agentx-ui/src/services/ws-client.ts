type Handler = (data: { type: string; id: string }) => void;

export class WsClient {
  private ws: WebSocket | null = null;
  private handlers: Handler[] = [];

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/api/v1/ws/ops`);
    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.handlers.forEach((h) => h(data));
      } catch { /* ignore */ }
    };
    this.ws.onclose = () => setTimeout(() => this.connect(), 3000);
  }

  on(handler: Handler) {
    this.handlers.push(handler);
  }
}

export const wsClient = new WsClient();
