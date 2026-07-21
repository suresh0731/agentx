import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { api, InstructionDetail } from '../../services/api-client.js';
import { wsClient, WsMessage } from '../../services/ws-client.js';
import {
  collectFieldCorrections,
  goldenSchemaToFormValues,
  renderConfidenceHeatmap,
  renderEditableFieldsForm,
  resolveFieldConfidences,
} from '../../utils/idp-display.js';
import '../shared/step-tracker.js';

@customElement('txn-modal')
export class TxnModal extends LightDomElement {
  @state() private detail: InstructionDetail | null = null;
  @state() private visible = false;
  @state() private editedFields: Record<string, string> = {};
  @state() private originalFields: Record<string, string> = {};
  @state() private reviewNote = '';
  @state() private saving = false;
  @state() private approving = false;
  private readonly wsHandler = (msg: WsMessage) => this.onWsMessage(msg);

  connectedCallback() {
    super.connectedCallback();
    wsClient.on(this.wsHandler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    wsClient.off(this.wsHandler);
  }

  private initFieldState(detail: InstructionDetail) {
    const values = goldenSchemaToFormValues(detail.golden_schema, detail.intake);
    this.editedFields = { ...values };
    this.originalFields = { ...values };
    this.reviewNote = '';
  }

  private hasUnsavedCorrections(): boolean {
    return Object.keys(collectFieldCorrections(this.editedFields, this.originalFields)).length > 0;
  }

  private onFieldChange(field: string, value: string) {
    this.editedFields = { ...this.editedFields, [field]: value };
  }

  private async onWsMessage(msg: WsMessage) {
    if (!this.visible || !this.detail) return;
    if (msg.id !== this.detail.ref) return;
    if (msg.type !== 'instruction_progress' && msg.type !== 'instruction_updated') return;
    if (this.hasUnsavedCorrections()) return;
    this.detail = await api.getInstruction(this.detail.ref);
    this.initFieldState(this.detail);
  }

  async show(ref: string) {
    this.detail = await api.getInstruction(ref);
    this.initFieldState(this.detail);
    this.visible = true;
  }

  close() {
    this.visible = false;
    this.detail = null;
    this.editedFields = {};
    this.originalFields = {};
    this.reviewNote = '';
  }

  private async saveCorrections() {
    if (!this.detail) return;
    const corrections = collectFieldCorrections(this.editedFields, this.originalFields);
    if (!Object.keys(corrections).length) return;

    this.saving = true;
    try {
      this.detail = await api.updateInstructionFields(this.detail.ref, {
        fields: corrections,
        note: this.reviewNote.trim() || undefined,
      });
      this.originalFields = { ...this.editedFields };
    } finally {
      this.saving = false;
    }
  }

  private async approve() {
    if (!this.detail || this.approving) return;
    this.approving = true;
    try {
      const corrections = collectFieldCorrections(this.editedFields, this.originalFields);
      await api.approveInstruction(this.detail.ref, {
        fields: Object.keys(corrections).length ? corrections : undefined,
        note: this.reviewNote.trim() || undefined,
      });
      this.dispatchEvent(new CustomEvent('approved', { detail: this.detail.ref, bubbles: true, composed: true }));
      this.close();
    } finally {
      this.approving = false;
    }
  }

  render() {
    if (!this.visible || !this.detail) return html``;
    const d = this.detail;
    const confidences = resolveFieldConfidences(d.field_confidences, d.intake);
    const hasCorrections = this.hasUnsavedCorrections();
    const canReview = d.journey?.heldStep !== undefined && d.journey.heldStep !== null;

    return html`
      <div class="modal-overlay" style="background:rgba(0,0,0,0.4);" @click=${(e: Event) => { if (e.target === e.currentTarget) this.close(); }}>
        <div class="modal-content" style="max-width:72rem;padding:0;" @click=${(e: Event) => e.stopPropagation()}>
          <div class="px-6 pt-5 pb-4 border-b border-gray-200 flex items-center justify-between" style="position:sticky;top:0;background:#fff;z-index:1;">
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
              <div class="section-label mb-1">Editable Extracted Fields</div>
              <p class="text-xs text-slate-500 mb-4">
                ${canReview
                  ? 'Correct extracted values before approving. Saved corrections are used in routing and reconciliation.'
                  : 'Review extracted field values. Corrections can be saved for audit before continuing.'}
              </p>
              ${renderEditableFieldsForm(this.editedFields, confidences, (field, value) => this.onFieldChange(field, value))}
            </div>

            <div class="mb-6 wireframe-card rounded-2xl p-5">
              <div class="section-label mb-2">Review Note (Added to Evidence Trail)</div>
              <textarea
                id="audit-note"
                placeholder="Explain your correction..."
                class="w-full h-24 text-sm"
                .value=${this.reviewNote}
                @input=${(e: Event) => { this.reviewNote = (e.target as HTMLTextAreaElement).value; }}
              ></textarea>
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

            <div class="flex flex-wrap gap-3 items-center">
              <button
                class="btn-outline"
                style="cursor:pointer;"
                ?disabled=${!hasCorrections || this.saving}
                @click=${() => this.saveCorrections()}
              >${this.saving ? 'Saving…' : 'Save Corrections'}</button>
              <button
                class="corp-btn-primary"
                style="border:none;cursor:pointer;padding:8px 20px;"
                ?disabled=${this.approving}
                @click=${() => this.approve()}
              >${this.approving ? 'Approving…' : 'Approve & Continue'}</button>
              <button class="btn-outline" @click=${() => this.close()}>Close</button>
              ${hasCorrections ? html`<span class="text-xs text-amber-600">Unsaved field corrections</span>` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'txn-modal': TxnModal; } }
