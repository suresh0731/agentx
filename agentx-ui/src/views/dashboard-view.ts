import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api, type KpiTile, type OpsMetric } from '../services/api-client.js';

const CHANNEL_ICONS: Record<string, string> = {
  SWIFT: 'fa-file-code',
  PDF: 'fa-file-pdf',
  Email: 'fa-envelope',
  Portal: 'fa-folder',
  API: 'fa-plug',
  'Client Template': 'fa-file-lines',
  Excel: 'fa-file-excel',
};

@customElement('dashboard-view')
export class DashboardView extends LightDomElement {
  @state() private data: Awaited<ReturnType<typeof api.getKpis>> | null = null;
  @state() private journey: Awaited<ReturnType<typeof api.getJourneyHealth>> | null = null;
  @state() private opsMetrics: Awaited<ReturnType<typeof api.getOpsMetrics>>['metrics'] = [];
  @state() private attention: Awaited<ReturnType<typeof api.getAttention>> | null = null;
  @state() private channels: Awaited<ReturnType<typeof api.getChannels>> = [];
  @state() private routing: { ta: number; fa: number; is: number } | null = null;
  @state() private intents: Awaited<ReturnType<typeof api.getIntents>> = [];
  @state() private pipelineOpen = false;

  async connectedCallback() {
    super.connectedCallback();
    await this.load();
  }

  async load() {
    [this.data, this.journey, this.opsMetrics, this.attention, this.channels, this.routing, this.intents] = await Promise.all([
      api.getKpis(), api.getJourneyHealth(), api.getOpsMetrics(), api.getAttention(),
      api.getChannels(), api.getRouting(), api.getIntents(),
    ]).then(([kpis, journey, ops, attention, channels, routing, intents]) => [
      kpis, journey, ops.metrics, attention, channels, routing, intents,
    ]);
  }

  private navigate(tab: string) {
    this.dispatchEvent(new CustomEvent('navigate-tab', { detail: tab, bubbles: true, composed: true }));
  }

  private toneClass(tone?: string) {
    if (tone === 'warning' || tone === 'danger') return 'text-amber-400';
    return 'text-emerald-400';
  }

  private renderPrimaryKpi(k: KpiTile, index: number) {
    const isHero = index === 0;
    return html`
      <div class="wireframe-card rounded-3xl p-6 ${isHero ? 'col-span-1 md:col-span-2 lg:col-span-1' : ''}">
        <div class="section-label">${k.label}</div>
        <div class="flex items-baseline gap-x-2 mt-2">
          <div class="${isHero ? 'text-6xl' : 'text-5xl'} font-semibold kpi-value">${k.value}</div>
          ${k.unit ? html`<div class="${isHero ? 'text-2xl' : 'text-xl'} ${this.toneClass(k.tone)}">${k.unit}</div>` : ''}
        </div>
        ${k.delta != null ? html`
          <div class="flex items-center gap-x-2 mt-3">
            <span class="text-blue-600 text-sm font-medium">+${k.delta}%</span>
            <span class="text-xs text-slate-400">${k.delta_label || ''}</span>
          </div>
        ` : k.footnote ? html`<div class="text-xs ${this.toneClass(k.tone)} mt-3">${k.footnote}</div>` : ''}
      </div>
    `;
  }

  private renderOpsMetric(m: OpsMetric) {
    const displayValue = m.key === 'repairs_mtd' ? m.value.toLocaleString() : m.value;
    return html`
      <div class="wireframe-card rounded-3xl p-5 ops-metric-card">
        <div class="flex items-center gap-3">
          <div class="ops-metric-icon"><i class="fa-solid ${m.icon || 'fa-chart-line'}"></i></div>
          <div class="section-label">${m.label}</div>
        </div>
        <div class="flex items-baseline gap-x-2">
          <div class="ops-metric-value kpi-value ${this.toneClass(m.tone)}">${displayValue}</div>
          ${m.unit ? html`<div class="text-xl ${this.toneClass(m.tone)}">${m.unit}</div>` : ''}
        </div>
        ${m.footnote ? html`<div class="text-[10px] text-slate-400">${m.footnote}</div>` : ''}
      </div>
    `;
  }

  render() {
    if (!this.data) return html`<p class="text-sm text-slate-400">Loading dashboard...</p>`;

    const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

    return html`
      <div class="flex items-end justify-between mb-6">
        <div>
          <h1 class="page-title">Operations Command Center</h1>
          <p class="page-subtitle">AI-powered STP Platform • ${today} • Real-time view</p>
        </div>
        <div class="flex items-center gap-x-2">
          <button class="btn-outline" @click=${() => this.load()}>
            <i class="fa-solid fa-sync-alt text-xs"></i>
            <span>Refresh</span>
          </button>
          <button class="corp-btn-primary px-5 h-9 text-sm flex items-center gap-x-2" style="border:none;cursor:pointer;">
            <i class="fa-solid fa-download text-xs"></i>
            <span>Export Report</span>
          </button>
        </div>
      </div>

      <div class="kpi-grid-primary">
        ${this.data.primary.map((k, i) => this.renderPrimaryKpi(k, i))}
      </div>

      <div class="kpi-grid-secondary">
        ${this.data.secondary.map((k) => html`
          <div class="wireframe-card rounded-2xl p-4">
            <div class="section-label">${k.label}</div>
            <div class="text-2xl font-semibold kpi-value mt-1 ${this.toneClass(k.tone)}">
              ${k.value}${k.unit ? html`<span class="text-sm ${this.toneClass(k.tone)}">${k.unit}</span>` : ''}
            </div>
            ${k.footnote ? html`<div class="text-[10px] text-slate-400 mt-1">${k.footnote}</div>` : ''}
          </div>
        `)}
      </div>

      ${this.opsMetrics.length ? html`
        <div class="ops-metrics-grid">
          ${this.opsMetrics.map((m) => this.renderOpsMetric(m))}
        </div>
      ` : ''}

      <div class="dashboard-row-2">
        <div class="wireframe-card rounded-3xl p-5">
          <div class="flex justify-between items-center mb-4">
            <div class="font-semibold">Journey Stage Performance</div>
            <span class="text-xs text-emerald-400">${this.journey?.overall_stp || 0}% completed full journey</span>
          </div>
          <div class="space-y-4">
            ${(this.journey?.stages || []).map((s) => html`
              <div>
                <div class="flex justify-between text-xs mb-1">
                  <div>${s.stage}. ${s.label}</div>
                  <div class="font-medium ${s.is_bottleneck ? 'text-amber-400' : ''}">${s.pass_rate}%</div>
                </div>
                <div class="bar-track">
                  <div class="${s.is_bottleneck ? 'bar-fill-amber' : 'bar-fill-emerald'}" style="width:${s.pass_rate}%"></div>
                </div>
                ${s.is_bottleneck ? html`<div class="text-[10px] text-amber-400 mt-0.5">Main bottleneck stage</div>` : ''}
              </div>
            `)}
          </div>
        </div>

        <div class="wireframe-card rounded-3xl p-5">
          <div class="font-semibold mb-4 flex items-center gap-x-2">
            <span>Attention Required</span>
            <span class="attention-badge">${this.attention?.total || 0}</span>
          </div>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between items-center"><div>High Priority Exceptions</div><div class="font-semibold text-red-400">${this.attention?.high_priority || 0}</div></div>
            <div class="flex justify-between items-center"><div>SLA at Risk (next 2h)</div><div class="font-semibold text-amber-400">${this.attention?.sla_at_risk || 0}</div></div>
            <div class="flex justify-between items-center"><div>Reconciliation Mismatches</div><div class="font-semibold text-red-400">${this.attention?.recon_mismatches || 0}</div></div>
            <div class="flex justify-between items-center"><div>Compliance Holds (AML)</div><div class="font-semibold text-amber-400">${this.attention?.aml_holds || 0}</div></div>
          </div>
          <button class="mt-4 w-full py-2 text-sm corp-btn-primary" style="border:none;cursor:pointer;" @click=${() => this.navigate('workbench')}>
            Go to Operations Workbench →
          </button>
          <button class="mt-2 btn-secondary-full" @click=${() => this.navigate('exceptions')}>
            View Exceptions List
          </button>
        </div>
      </div>

      <div class="kpi-grid-3">
        <div class="wireframe-card rounded-3xl p-5">
          <div class="font-semibold mb-4">Channel Performance</div>
          <div class="space-y-4 text-sm">
            ${this.channels.map((c) => html`
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-x-2">
                  <i class="fa-solid ${CHANNEL_ICONS[c.name] || 'fa-circle'} text-emerald-400"></i>
                  <span>${c.name}</span>
                </div>
                <div class="text-right">
                  <span class="font-medium">${c.volume.toLocaleString()}</span>
                  <span class="text-xs text-emerald-400 ml-2">${c.stp_rate}% STP</span>
                </div>
              </div>
            `)}
          </div>
        </div>

        <div class="wireframe-card rounded-3xl p-5">
          <div class="font-semibold mb-4">Routing Distribution (TA / FA / IS)</div>
          ${this.routing ? html`
            <div class="space-y-3 text-sm">
              <div>
                <div class="flex justify-between text-xs mb-1"><span>Transfer Agent (TA)</span><span class="font-medium">${this.routing.ta}%</span></div>
                <div class="bar-track-sm"><div class="bar-fill-emerald" style="width:${this.routing.ta}%"></div></div>
              </div>
              <div>
                <div class="flex justify-between text-xs mb-1"><span>Fund Accounting (FA)</span><span class="font-medium">${this.routing.fa}%</span></div>
                <div class="bar-track-sm"><div class="bar-fill-emerald" style="width:${this.routing.fa}%"></div></div>
              </div>
              <div>
                <div class="flex justify-between text-xs mb-1"><span>Investor Servicing (IS)</span><span class="font-medium">${this.routing.is}%</span></div>
                <div class="bar-track-sm"><div class="bar-fill-emerald" style="width:${this.routing.is}%"></div></div>
              </div>
            </div>
          ` : ''}
        </div>

        <div class="wireframe-card rounded-3xl p-5">
          <div class="font-semibold mb-4">STP by Intent</div>
          <div class="space-y-3 text-sm">
            ${this.intents.map((i) => html`
              <div class="flex justify-between"><span>${i.intent}</span><span class="font-medium text-emerald-400">${i.stp_rate}%</span></div>
            `)}
          </div>
        </div>
      </div>

      <div class="mt-6">
        <button class="pipeline-toggle wireframe-card rounded-2xl px-5 py-4 hover:border-blue-300 transition-colors group"
          @click=${() => { this.pipelineOpen = !this.pipelineOpen; }}>
          <div class="flex items-center gap-3">
            <div class="pipeline-icon-box">
              <i class="fa-solid fa-route text-blue-600 text-sm"></i>
            </div>
            <div>
              <div class="font-semibold text-sm">Processing Pipeline Reference</div>
              <div class="text-xs text-slate-500">6-stage flow every instruction follows • 98% confidence gate</div>
            </div>
          </div>
          <i class="fa-solid fa-chevron-down text-gray-500 group-hover:text-gray-600" style="transition:transform 0.2s;${this.pipelineOpen ? 'transform:rotate(180deg);' : ''}"></i>
        </button>
        ${this.pipelineOpen ? html`
          <div class="mt-3 wireframe-card rounded-3xl p-5">
            <div class="pipeline-grid">
              ${[
                ['fa-inbox', '1. Ingestion'],
                ['fa-search', '2. Detect'],
                ['fa-check-double', '3. Validate'],
                ['fa-tools', '4. Repair'],
                ['fa-share', '5. Route'],
                ['fa-scale-balanced', '6. Reconcile'],
              ].map(([icon, label]) => html`
                <div class="pipeline-step">
                  <i class="fa-solid ${icon} text-blue-600 text-sm"></i>
                  <div class="text-xs font-medium mt-1.5">${label}</div>
                </div>
              `)}
            </div>
            <div class="text-xs text-slate-400 flex items-center gap-2">
              <i class="fa-solid fa-circle-info text-emerald-500"></i>
              Instructions below <strong class="text-amber-400">98% confidence</strong> are held for human review before auto-creation.
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'dashboard-view': DashboardView; } }
