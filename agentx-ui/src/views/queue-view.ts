import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api, InstructionSummary } from '../services/api-client.js';
import { wsClient, WsMessage } from '../services/ws-client.js';
import '../components/shared/step-tracker.js';

function statusStyle(status: string) {
  const s = status.toLowerCase();
  if (s.includes('exception') || s.includes('recon')) return 'background:#fff7e6;color:#d48806;';
  if (s.includes('reconciled') || s.includes('auto')) return 'background:#f6ffed;color:#389e0d;';
  if (s.includes('routed')) return 'background:#e6f4ff;color:#0958d9;';
  if (s.includes('processing')) return 'background:#f6ffed;color:#389e0d;';
  return 'background:#f5f5f5;color:#595959;';
}

function confClass(val: number) {
  if (val >= 98) return 'text-emerald-400';
  if (val >= 90) return 'text-amber-400';
  return 'text-red-400';
}

@customElement('queue-view')
export class QueueView extends LightDomElement {
  @state() private rows: InstructionSummary[] = [];
  private readonly wsHandler = (msg: WsMessage) => this.onWsMessage(msg);

  async connectedCallback() {
    super.connectedCallback();
    this.rows = await api.getInstructions();
    wsClient.on(this.wsHandler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    wsClient.off(this.wsHandler);
  }

  private onWsMessage(msg: WsMessage) {
    if (msg.type !== 'instruction_progress' && msg.type !== 'instruction_updated') return;
    if (!msg.instruction) return;
    const idx = this.rows.findIndex((r) => r.ref === msg.id);
    if (idx >= 0) {
      const next = [...this.rows];
      next[idx] = msg.instruction;
      this.rows = next;
    } else {
      this.rows = [...this.rows, msg.instruction];
    }
  }

  private open(ref: string) {
    this.dispatchEvent(new CustomEvent('open-txn', { detail: ref, bubbles: true, composed: true }));
  }

  render() {
    return html`
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="page-title">Transaction Queue</h1>
          <p class="page-subtitle">Live instructions across all intake channels</p>
        </div>
      </div>

      <div class="filter-bar">
        <div>
          <label>Instruction ID</label>
          <input type="text" placeholder="Enter ID" style="width:160px;" />
        </div>
        <div>
          <label>Party / Asset</label>
          <input type="text" placeholder="Search..." style="width:192px;" />
        </div>
        <select><option>All Statuses</option><option>Auto Created</option><option>Exception Queue</option></select>
        <select><option>All Channels</option><option>SWIFT</option><option>PDF</option><option>Email</option><option>API</option><option>Portal</option></select>
        <select><option>All Intents</option><option>Subscription</option><option>Redemption</option></select>
        <select><option>All Destinations</option><option>TA</option><option>FA</option><option>IS</option></select>
        <select><option>All Confidence</option><option>≥ 98% (Auto eligible)</option><option>&lt; 98% (Review required)</option></select>
        <button class="corp-btn-primary px-6 h-9 text-xs ml-auto" style="border:none;cursor:pointer;">Search</button>
      </div>

      <div class="wireframe-card rounded-lg overflow-x-auto">
        <table class="queue-table">
          <thead>
            <tr>
              <th>Instruction ID</th>
              <th>File</th>
              <th>Source</th>
              <th>Intent</th>
              <th>Destination</th>
              <th class="center">Confidence</th>
              <th class="center">Status</th>
              <th style="min-width:240px">Processing Step</th>
            </tr>
          </thead>
          <tbody>
            ${this.rows.map((r) => html`
              <tr class="cursor-pointer" @click=${() => this.open(r.ref)}>
                <td class="mono font-medium">${r.ref}</td>
                <td class="truncate" style="max-width:200px" title=${r.filename || ''}>${r.filename || '—'}</td>
                <td>${r.source}</td>
                <td>${r.intent || '—'}</td>
                <td>${r.dest || '—'}</td>
                <td class="center font-medium ${confClass(r.confValue)}">${r.confValue > 0 ? r.conf : '—'}</td>
                <td class="center"><span class="status-pill" style="${statusStyle(r.status)}">${r.status}</span></td>
                <td><ax-step-tracker .journey=${r.journey}></ax-step-tracker></td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'queue-view': QueueView; } }
