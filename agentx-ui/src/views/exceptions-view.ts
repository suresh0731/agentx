import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api } from '../services/api-client.js';
import '../components/shared/step-tracker.js';

@customElement('exceptions-view')
export class ExceptionsView extends LightDomElement {
  @state() private rows: Awaited<ReturnType<typeof api.getExceptions>> = [];

  async connectedCallback() {
    super.connectedCallback();
    this.rows = await api.getExceptions();
  }

  private open(ref: string) {
    this.dispatchEvent(new CustomEvent('open-txn', { detail: ref, bubbles: true, composed: true }));
  }

  render() {
    return html`
      <h1 class="page-title mb-1">Exceptions</h1>
      <p class="page-subtitle mb-5">Instructions requiring human review — failure step shown inline</p>
      <div class="wireframe-card rounded-lg overflow-x-auto">
        <table class="queue-table" style="min-width:1000px;font-size:14px;">
          <thead>
            <tr>
              <th style="padding-left:20px;">Instruction ID</th>
              <th>Issue</th>
              <th style="min-width:260px">Where It Stopped</th>
              <th class="center">Priority</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${this.rows.map((r) => html`
              <tr class="cursor-pointer" @click=${() => this.open(r.ref)}>
                <td style="padding-left:20px;"><strong class="mono">${r.ref}</strong></td>
                <td class="text-amber-400">${r.issue}</td>
                <td><ax-step-tracker .journey=${r.journey}></ax-step-tracker></td>
                <td class="center">
                  <span class="status-pill" style="background:${r.priority === 'HIGH' ? '#fff1f0' : '#fff7e6'};color:${r.priority === 'HIGH' ? '#cf1322' : '#d48806'};">
                    ${r.priority}
                  </span>
                </td>
                <td>
                  <button class="corp-btn-primary" style="font-size:11px;padding:4px 12px;border:none;cursor:pointer;"
                    @click=${(e: Event) => { e.stopPropagation(); this.open(r.ref); }}>Review</button>
                </td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'exceptions-view': ExceptionsView; } }
