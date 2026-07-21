import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api, WorkbenchCard } from '../services/api-client.js';
import { wsClient, WsMessage } from '../services/ws-client.js';
import { WORKBENCH_STAGES, confClass, formatSla, slaClass } from '../constants/index.js';
import '../components/shared/step-tracker.js';

@customElement('workbench-view')
export class WorkbenchView extends LightDomElement {
  @state() private cards: WorkbenchCard[] = [];
  @state() private insights: Awaited<ReturnType<typeof api.getInsights>> | null = null;
  @state() private showInsights = false;
  @state() private draggedId: string | null = null;
  @state() private filterIntent = '';
  @state() private filterView = 'all';
  private readonly wsHandler = (msg: WsMessage) => this.onWsMessage(msg);

  private readonly approvedHandler = () => { void this.load(); };

  async connectedCallback() {
    super.connectedCallback();
    await this.load();
    wsClient.on(this.wsHandler);
    this.addEventListener('approved', this.approvedHandler);
    setInterval(() => this.tickSla(), 60000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    wsClient.off(this.wsHandler);
    this.removeEventListener('approved', this.approvedHandler);
  }

  private onWsMessage(msg: WsMessage) {
    if (msg.type === 'workbench_updated') {
      void this.load();
      return;
    }
    if ((msg.type === 'instruction_progress' || msg.type === 'instruction_updated') && msg.workbench) {
      this.upsertCard(msg.workbench);
    }
  }

  private upsertCard(card: WorkbenchCard) {
    const idx = this.cards.findIndex((c) => c.id === card.id);
    if (idx >= 0) {
      const next = [...this.cards];
      next[idx] = card;
      this.cards = next;
    } else {
      this.cards = [...this.cards, card];
    }
  }

  async load() {
    [this.cards, this.insights] = await Promise.all([api.getWorkbench(), api.getInsights()]);
  }

  tickSla() {
    this.cards = this.cards.map((c) => ({ ...c, slaRemaining: Math.max(-999, c.slaRemaining - 1) }));
  }

  private filteredCards() {
    return this.cards.filter((c) => {
      if (this.filterIntent && c.intent !== this.filterIntent) return false;
      if (this.filterView === 'review' && c.stage !== 'review') return false;
      if (this.filterView === 'exceptions' && !['review', 'escalated', 'rejected'].includes(c.stage)) return false;
      return true;
    });
  }

  private openWorkspace(id: string) {
    this.dispatchEvent(new CustomEvent('open-workspace', { detail: id, bubbles: true, composed: true }));
  }

  private onDragStart(e: DragEvent, id: string) {
    this.draggedId = id;
    e.dataTransfer?.setData('text/plain', id);
    (e.target as HTMLElement).classList.add('dragging');
  }

  private onDragEnd(e: DragEvent) {
    (e.target as HTMLElement).classList.remove('dragging');
  }

  private async onDrop(e: DragEvent, stage: string) {
    e.preventDefault();
    const id = this.draggedId || e.dataTransfer?.getData('text/plain');
    if (!id) return;
    await api.patchWorkbenchStage(id, stage);
    await this.load();
    this.draggedId = null;
  }

  renderCard(c: WorkbenchCard) {
    return html`
      <div class="kanban-card" draggable="true"
        @dragstart=${(e: DragEvent) => this.onDragStart(e, c.id)}
        @dragend=${(e: DragEvent) => this.onDragEnd(e)}
        @click=${() => this.openWorkspace(c.id)}>
        <div class="flex justify-between text-[10px] mb-1">
          <span class="mono">${c.ref}</span>
          <span style="background:#f0f0f0;padding:2px 6px;border-radius:999px;color:#595959;">${c.intent}</span>
        </div>
        <div class="text-xs font-semibold">${c.party}</div>
        <div class="text-[10px] text-slate-400 mt-1">${c.source} · ${c.amount}</div>
        ${c.confidence > 0 ? html`
          <div class="flex items-center gap-2 mt-2">
            <div class="conf-bar" style="flex:1;"><div class="${confClass(c.confidence)}" style="width:${c.confidence}%;height:100%;"></div></div>
            <span class="text-[9px]">${c.confidence}%</span>
          </div>` : html`<div class="text-[9px] text-slate-400 mt-2">Pending validation</div>`}
        <ax-step-tracker variant="card" context="workbench" .journey=${c.journey}></ax-step-tracker>
        <div class="flex justify-between text-[10px] mt-2">
          <span class="${slaClass(c.slaRemaining)}">${formatSla(c.slaRemaining)}</span>
          <span class="text-slate-400">${c.assignee}</span>
        </div>
      </div>
    `;
  }

  render() {
    const filtered = this.filteredCards();
    return html`
      <div class="flex items-center justify-between mb-3 shrink-0">
        <div>
          <h1 class="page-title">AI Operations Workbench</h1>
          <p class="page-subtitle">Review queue (Kanban) · each card tracks the <span class="text-emerald-400">6-stage STP journey</span> from ingestion to reconciliation</p>
        </div>
        <div class="flex items-center gap-2">
          <select class="bg-white border border-gray-300 rounded px-3 h-8 text-xs"
            .value=${this.filterIntent}
            @change=${(e: Event) => { this.filterIntent = (e.target as HTMLSelectElement).value; }}>
            <option value="">All Intents</option>
            <option>Subscription</option>
            <option>Redemption</option>
            <option>Switch</option>
            <option>Transfer</option>
          </select>
          <select class="bg-white border border-gray-300 rounded px-3 h-8 text-xs"
            .value=${this.filterView}
            @change=${(e: Event) => { this.filterView = (e.target as HTMLSelectElement).value; }}>
            <option value="all">All Requests</option>
            <option value="review">Needs Review Only</option>
            <option value="exceptions">Exceptions & Escalations</option>
          </select>
          <button class="btn-outline-sm" @click=${() => this.load()}><i class="fa-solid fa-sync-alt"></i> Refresh</button>
          <button class="corp-btn-primary px-4 h-8 text-xs flex items-center gap-1.5" style="border:none;cursor:pointer;" @click=${() => { this.showInsights = !this.showInsights; }}>
            <i class="fa-solid fa-chart-pie"></i>
            <span class="hidden sm:inline">Insights</span>
          </button>
        </div>
      </div>

      ${this.insights ? html`
        <div class="workbench-stats-strip">
          <div class="wb-stat-chip">
            <i class="fa-solid fa-layer-group text-slate-500 text-[10px]"></i>
            <span class="text-slate-400">Active</span>
            <span class="wb-stat-value text-emerald-400">${this.insights.total}</span>
          </div>
          <div class="wb-stat-chip wb-stat-warn">
            <i class="fa-solid fa-user-check text-amber-500/80 text-[10px]"></i>
            <span class="text-slate-400">In review</span>
            <span class="wb-stat-value text-amber-400">${this.insights.in_review}</span>
          </div>
          <div class="wb-stat-chip wb-stat-warn">
            <i class="fa-regular fa-clock text-amber-500/80 text-[10px]"></i>
            <span class="text-slate-400">SLA at risk</span>
            <span class="wb-stat-value text-amber-400">${this.insights.sla_at_risk}</span>
          </div>
          <div class="wb-stat-chip wb-stat-danger">
            <i class="fa-solid fa-triangle-exclamation text-red-400/80 text-[10px]"></i>
            <span class="text-slate-400">Breached</span>
            <span class="wb-stat-value text-red-400">${this.insights.sla_breached}</span>
          </div>
          <div class="wb-stat-chip">
            <i class="fa-solid fa-gauge-high text-slate-500 text-[10px]"></i>
            <span class="text-slate-400">Avg conf</span>
            <span class="wb-stat-value">${this.insights.avg_confidence}%</span>
          </div>
          <button class="wb-stat-chip hover:border-blue-300 cursor-pointer ml-auto" style="background:#fff;" @click=${() => { this.showInsights = true; }}>
            <i class="fa-solid fa-chart-simple text-blue-600 text-[10px]"></i>
            <span class="text-gray-600">Stage breakdown</span>
            <i class="fa-solid fa-chevron-right text-[9px] text-gray-400"></i>
          </button>
        </div>
      ` : ''}

      <div class="workbench-layout flex flex-col min-h-0 flex-1">
        <div class="kanban-board">
          ${WORKBENCH_STAGES.map((stage) => {
            const cards = filtered.filter((c) => c.stage === stage.id);
            return html`
              <div class="kanban-column col-${stage.id}">
                <div class="kanban-column-header">
                  <i class="fa-solid ${stage.icon}" style="color:${stage.color};margin-right:6px;"></i>
                  ${stage.label}
                  <span style="background:#f0f0f0;padding:2px 6px;border-radius:999px;font-size:10px;margin-left:6px;">${cards.length}</span>
                </div>
                <div class="kanban-column-body"
                  @dragover=${(e: DragEvent) => { e.preventDefault(); (e.currentTarget as HTMLElement).classList.add('drag-over'); }}
                  @dragleave=${(e: DragEvent) => { (e.currentTarget as HTMLElement).classList.remove('drag-over'); }}
                  @drop=${(e: DragEvent) => { (e.currentTarget as HTMLElement).classList.remove('drag-over'); this.onDrop(e, stage.id); }}>
                  ${cards.map((c) => this.renderCard(c))}
                </div>
              </div>
            `;
          })}
        </div>
      </div>

      <div class="workbench-insights-backdrop ${this.showInsights ? 'open' : ''}" @click=${() => { this.showInsights = false; }}></div>
      <aside class="workbench-insights-drawer ${this.showInsights ? 'open' : ''}">
        <div class="px-4 py-3 border-b border-gray-200 flex items-center justify-between shrink-0">
          <div>
            <div class="font-semibold text-sm">Queue Insights</div>
            <div class="text-[10px] text-gray-500">Live workbench analytics</div>
          </div>
          <button class="w-9 h-9 rounded-lg hover:bg-gray-50 text-gray-500 flex items-center justify-center" style="border:none;background:none;cursor:pointer;" @click=${() => { this.showInsights = false; }}>
            <i class="fa-solid fa-xmark text-sm"></i>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          ${this.insights ? html`
            <div class="wireframe-card rounded-2xl p-4 mb-3">
              <div class="text-2xl font-semibold kpi-value text-emerald-400">${this.insights.total}</div>
              <div class="text-xs text-slate-400">Active requests</div>
            </div>
            <div class="wireframe-card rounded-2xl p-4 mb-3">
              <div class="section-label mb-2">By Review Queue</div>
              <div class="space-y-2 text-xs">
                ${Object.entries(this.insights.distribution).map(([k, v]) => html`
                  <div class="flex justify-between"><span>${k}</span><span class="font-medium">${v}</span></div>
                `)}
              </div>
            </div>
            <div class="wireframe-card rounded-2xl p-4 mb-3">
              <div class="section-label mb-2">SLA Health</div>
              <div class="flex justify-between text-xs mb-1"><span>On track</span><span class="text-emerald-400 font-medium">${this.insights.total - this.insights.sla_at_risk - this.insights.sla_breached}</span></div>
              <div class="flex justify-between text-xs mb-1"><span>At risk</span><span class="text-amber-400 font-medium">${this.insights.sla_at_risk}</span></div>
              <div class="flex justify-between text-xs"><span>Breached</span><span class="text-red-400 font-medium">${this.insights.sla_breached}</span></div>
            </div>
            <div class="wireframe-card rounded-2xl p-4 mb-3">
              <div class="section-label mb-2">Avg Confidence</div>
              <div class="text-xl font-semibold kpi-value">${this.insights.avg_confidence}%</div>
              <div class="conf-bar mt-2"><div class="conf-fill-high" style="width:${this.insights.avg_confidence}%;height:100%;"></div></div>
            </div>
            <div class="wireframe-card rounded-2xl p-4">
              <div class="section-label mb-2">Paths Today</div>
              <div class="space-y-2 text-xs">
                ${Object.entries(this.insights.paths_today).map(([k, v]) => html`
                  <div class="flex justify-between"><span>${k}</span><span class="text-emerald-400">${v}</span></div>
                `)}
              </div>
            </div>
          ` : ''}
        </div>
      </aside>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'workbench-view': WorkbenchView; } }
