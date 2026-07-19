import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { api, InstructionDetail } from '../../services/api-client.js';
import { renderConfidenceHeatmap, renderGoldenSchemaTable } from '../../utils/idp-display.js';
import '../shared/step-tracker.js';

@customElement('txn-modal')
export class TxnModal extends LightDomElement {
  @state() private detail: InstructionDetail | null = null;
  @state() private visible = false;

  async show(ref: string) {
    this.detail = await api.getInstruction(ref);
    this.visible = true;
  }

  close() {
    this.visible = false;
    this.detail = null;
  }

  private async approve() {
    if (!this.detail) return;
    await api.approveInstruction(this.detail.ref);
    this.dispatchEvent(new CustomEvent('approved', { detail: this.detail.ref, bubbles: true, composed: true }));
    this.close();
  }

  render() {
    if (!this.visible || !this.detail) return html``;
    const d = this.detail;
    return html`
      <div class="modal-overlay" style="background:rgba(0,0,0,0.4);" @click=${(e: Event) => { if (e.target === e.currentTarget) this.close(); }}>
        <div class="modal-content" style="max-width:72rem;padding:0;" @click=${(e: Event) => e.stopPropagation()}>
          <div class="px-6 pt-5 pb-4 border-b border-gray-200 flex items-center justify-between" style="position:sticky;top:0;background:#fff;">
            <div>
              <div class="mono text-2xl font-semibold text-gray-900">${d.ref}</div>
              <div class="text-blue-600 text-sm">${d.meta || ''}</div>
            </div>
            <button class="text-3xl text-gray-400 hover:text-gray-700 px-3" style="border:none;background:none;cursor:pointer;" @click=${() => this.close()}>&times;</button>
          </div>

          <div class="p-6">
            <div class="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="section-label mb-2">Confidence Score</div>
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm">
                  <strong style="font-size:24px;color:var(--corp-blue);">${d.confidence}%</strong>
                </div>
              </div>
              <div>
                <div class="section-label mb-2">Reconciliation Status</div>
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm">${d.recon_detail || d.recon_status || '—'}</div>
              </div>
            </div>

            ${d.stage_label ? html`
              <div class="mb-6">
                <div class="section-label mb-2">Current Stage in Journey</div>
                <span class="corp-pill">${d.stage_label}</span>
              </div>
            ` : ''}

            <div class="mb-4">
              <div class="section-label mb-2">Processing Step</div>
              <ax-step-tracker variant="workspace" .journey=${d.journey}></ax-step-tracker>
            </div>

            <div class="mb-6 wireframe-card rounded-2xl p-5">
              <div class="section-label mb-3">Golden Transaction Schema</div>
              ${renderGoldenSchemaTable(d.golden_schema, d.intake)}
            </div>

            <div class="mb-6 wireframe-card rounded-2xl p-5">
              <div class="section-label mb-3">Confidence Heatmap — Field-Level Scores</div>
              ${renderConfidenceHeatmap(d.field_confidences, d.intake)}
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <div class="section-label mb-2">Processing Decisions</div>
                ${(d.decisions || []).map((x: string) => html`<div class="text-sm py-1"><i class="fa-solid fa-check text-emerald-400 mr-2"></i>${x}</div>`)}
              </div>
              <div>
                <div class="section-label mb-2">Repair Notes</div>
                ${(d.repair_notes || []).map((x: string) => html`<div class="text-sm py-1 text-gray-600">${x}</div>`)}
              </div>
            </div>

            <div class="flex gap-3">
              <button class="corp-btn-primary" style="border:none;cursor:pointer;padding:8px 20px;" @click=${() => this.approve()}>Approve & Continue</button>
              <button class="btn-outline" @click=${() => this.close()}>Close</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'txn-modal': TxnModal; } }
