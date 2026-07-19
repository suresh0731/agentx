import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { api, WorkbenchCard } from '../../services/api-client.js';
import { riskColor, formatSla, slaClass } from '../../constants/index.js';
import '../shared/step-tracker.js';

@customElement('review-workspace')
export class ReviewWorkspace extends LightDomElement {
  @state() private card: WorkbenchCard | null = null;
  @state() private visible = false;

  async show(id: string) {
    this.card = await api.getWorkbenchDetail(id);
    this.visible = true;
  }

  close() {
    this.visible = false;
    this.card = null;
  }

  private async approve() {
    if (!this.card) return;
    await api.approveInstruction(this.card.ref);
    this.dispatchEvent(new CustomEvent('approved', { detail: this.card.ref, bubbles: true, composed: true }));
    this.close();
  }

  render() {
    if (!this.visible || !this.card) return html``;
    const c = this.card;
    return html`
      <div id="review-workspace" class="fixed inset-0 z-[600] bg-gray-50 flex flex-col" style="position:fixed;inset:0;z-index:600;background:#f9fafb;display:flex;flex-direction:column;">
        <div class="border-b border-gray-200 bg-white px-6 py-3 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-4">
            <button class="w-9 h-9 rounded-lg border border-gray-300 hover:bg-gray-50 flex items-center justify-center text-gray-700" style="cursor:pointer;background:#fff;" @click=${() => this.close()}>
              <i class="fa-solid fa-arrow-left text-sm"></i>
            </button>
            <div>
              <div class="mono text-lg font-semibold text-gray-900">${c.ref}</div>
              <div class="text-xs text-blue-600">${c.intent} · ${c.party}</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <div class="${slaClass(c.slaRemaining)} text-sm font-medium">${formatSla(c.slaRemaining)}</div>
            <button class="text-gray-400 hover:text-gray-700 text-2xl px-2" style="border:none;background:none;cursor:pointer;" @click=${() => this.close()}>&times;</button>
          </div>
        </div>

        <div class="border-b border-gray-200 bg-white px-6 py-4 shrink-0">
          <div style="max-width:72rem;margin:0 auto;">
            <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
              <div class="flex items-center gap-2">
                <span class="section-label">Transaction Journey</span>
                <span class="text-[10px] text-slate-600 hidden sm:inline">Ingest → Detect → Validate → Repair → Route → Reconcile</span>
              </div>
              <span class="ws-queue-pill" style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;">${c.stage}</span>
            </div>
            <ax-step-tracker variant="workspace" context="workbench" .journey=${c.journey}></ax-step-tracker>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6" style="flex:1;overflow-y:auto;padding:24px;">
          <div style="max-width:64rem;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:20px;">
            <div class="wireframe-card rounded-2xl p-5" style="grid-column:span 2;">
              <div class="section-label mb-3">Request Summary</div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div><div class="text-xs text-slate-400">Investor Name</div><div class="font-medium">${c.party}</div></div>
                <div><div class="text-xs text-slate-400">Amount</div><div class="font-medium">${c.amount}</div></div>
                <div><div class="text-xs text-slate-400">Source</div><div class="font-medium">${c.source}</div></div>
                <div><div class="text-xs text-slate-400">Assignee</div><div class="font-medium">${c.assignee}</div></div>
              </div>
            </div>

            <div class="wireframe-card rounded-2xl p-5">
              <div class="section-label mb-3">AI Findings</div>
              <div class="space-y-2 text-xs">
                ${c.findings.map((f: string) => html`<div>${f}</div>`)}
              </div>
            </div>

            <div class="wireframe-card rounded-2xl p-5">
              <div class="section-label mb-3">Risk Score</div>
              <div class="flex items-center gap-4">
                <div class="text-5xl font-semibold kpi-value">${c.risk}</div>
                <div class="flex-1">
                  <div class="text-xs text-slate-400 mb-2">Composite risk index</div>
                  <div class="bar-track"><div style="width:${c.risk}%;height:100%;background:${riskColor(c.risk)};border-radius:999px;"></div></div>
                </div>
              </div>
            </div>

            <div class="wireframe-card rounded-2xl p-5" style="grid-column:span 2;">
              <div class="section-label mb-3">Confidence Heatmap — Field-Level Scores</div>
              <div class="heatmap-grid">
                ${Object.entries(c.fields).map(([k, v]: [string, number]) => html`
                  <div class="heatmap-cell ${v >= 95 ? 'heat-high' : v >= 80 ? 'heat-med' : v > 0 ? 'heat-low' : ''}">${k}<br><strong>${v}%</strong></div>
                `)}
              </div>
            </div>

            <div class="wireframe-card rounded-2xl p-5" style="grid-column:span 2;">
              <div class="section-label mb-3">Explainability Panel</div>
              <div id="ws-explain" class="text-xs text-gray-600 leading-relaxed bg-gray-50 rounded-xl p-4 border border-gray-200">${c.explain}</div>
            </div>

            <div class="wireframe-card rounded-2xl p-5">
              <div class="section-label mb-3">Review Timeline</div>
              <div class="space-y-3 text-xs">
                ${c.timeline.map((t: string) => html`<div class="text-slate-400">${t}</div>`)}
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-gray-200 bg-white px-6 py-4 flex items-center justify-between shrink-0" style="padding-right:96px;">
          <div class="text-xs text-gray-500">Select an action to advance this request</div>
          <div class="flex flex-wrap justify-end gap-2">
            <button class="corp-btn-primary" style="border:none;cursor:pointer;" @click=${() => this.approve()}>Approve</button>
            <button class="btn-outline-sm" @click=${() => this.close()}>Back to Board</button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'review-workspace': ReviewWorkspace; } }
