import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api } from '../services/api-client.js';

@customElement('audit-view')
export class AuditView extends LightDomElement {
  @state() private events: Awaited<ReturnType<typeof api.getAudit>> = [];

  async connectedCallback() {
    super.connectedCallback();
    this.events = await api.getAudit();
  }

  render() {
    return html`
      <h1 class="page-title mb-5">Audit & Evidence Trail</h1>
      <div class="wireframe-card rounded-3xl p-6">
        <div class="text-xs text-slate-400 mb-4">Complete immutable record of every stage, decision and correction</div>
        <div class="space-y-4 text-sm">
          ${this.events.map((e) => html`
            <div class="border-l-2 border-emerald-500 pl-4">
              <div class="font-medium">${e.instruction_id} • ${e.summary}</div>
              <div class="text-xs text-emerald-400">${e.detail || ''}${e.detail ? ' • ' : ''}${e.actor} • ${e.timestamp}</div>
            </div>
          `)}
        </div>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'audit-view': AuditView; } }
