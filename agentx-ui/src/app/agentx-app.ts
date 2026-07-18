import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api } from '../services/api-client.js';
import { wsClient } from '../services/ws-client.js';
import '../views/dashboard-view.js';
import '../views/queue-view.js';
import '../views/exceptions-view.js';
import '../views/workbench-view.js';
import '../views/audit-view.js';
import '../views/configuration-view.js';
import '../components/transaction/txn-modal.js';
import type { TxnModal } from '../components/transaction/txn-modal.js';
import '../components/workspace/review-workspace.js';
import type { ReviewWorkspace } from '../components/workspace/review-workspace.js';
import '../components/assistant/assistant-panel.js';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'fa-chart-line' },
  { id: 'queue', label: 'Transaction Queue', icon: 'fa-list-check' },
  { id: 'exceptions', label: 'Exceptions', icon: 'fa-exclamation-triangle', badge: true },
  { id: 'workbench', label: 'Operations Workbench', icon: 'fa-table-columns', badge: true },
  { id: 'audit', label: 'Audit & Evidence', icon: 'fa-history' },
  { id: 'configuration', label: 'Configuration', icon: 'fa-cog' },
];

@customElement('agentx-app')
export class AgentxApp extends LightDomElement {
  @state() private tab = 'dashboard';
  @state() private user = 'SCB User';
  @state() private toast = '';
  @state() private workbenchBadge = 0;
  @state() private exceptionsBadge = 0;

  async connectedCallback() {
    super.connectedCallback();
    const me = await api.getMe();
    this.user = me.display_name;
    wsClient.connect();
    wsClient.on(() => this.refreshBadges());
    await this.refreshBadges();
    this.addEventListener('open-txn', ((e: CustomEvent) => {
      (document.querySelector('txn-modal') as TxnModal | null)?.show(e.detail);
    }) as EventListener);
    this.addEventListener('open-workspace', ((e: CustomEvent) => {
      (document.querySelector('review-workspace') as ReviewWorkspace | null)?.show(e.detail);
    }) as EventListener);
    this.addEventListener('approved', ((e: CustomEvent) => {
      this.toast = `${e.detail} approved — journey continued`;
      setTimeout(() => { this.toast = ''; }, 3000);
    }) as EventListener);
    this.addEventListener('navigate-tab', ((e: CustomEvent) => {
      this.tab = e.detail;
    }) as EventListener);
  }

  async refreshBadges() {
    const [cards, attention] = await Promise.all([api.getWorkbench(), api.getAttention()]);
    this.workbenchBadge = cards.filter((c) => ['submitted', 'validation', 'review', 'escalated'].includes(c.stage)).length;
    this.exceptionsBadge = attention.total;
  }

  private setTab(id: string) {
    this.tab = id;
  }

  private userInitials() {
    return this.user.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
  }

  renderView() {
    switch (this.tab) {
      case 'dashboard': return html`<dashboard-view></dashboard-view>`;
      case 'queue': return html`<queue-view></queue-view>`;
      case 'exceptions': return html`<exceptions-view></exceptions-view>`;
      case 'workbench': return html`<workbench-view></workbench-view>`;
      case 'audit': return html`<audit-view></audit-view>`;
      case 'configuration': return html`<configuration-view></configuration-view>`;
      default: return html``;
    }
  }

  render() {
    return html`
      <header>
        <div class="corp-top-bar">
          <div class="px-6 h-12 flex items-center justify-between">
            <span class="corp-top-bar-title">AgentX — AI-powered STP Platform</span>
            <div class="flex items-center gap-x-5">
              <button class="corp-top-link hidden sm:flex items-center gap-2" style="background:none;border:none;cursor:pointer;" @click=${() => (document.querySelector('assistant-panel') as { toggle: () => void } | null)?.toggle()}>
                <i class="fa-solid fa-wand-magic-sparkles text-xs"></i>
                <span>Assistant</span>
              </button>
              <a href="#" class="corp-top-link">Main</a>
            </div>
          </div>
        </div>
        <div class="corp-hero-banner">
          <div class="relative z-10 px-6 py-5 flex items-center justify-between gap-6">
            <div>
              <h1 class="corp-hero-title">AgentX</h1>
              <p class="corp-hero-subtitle">Empowering fund operations with intelligent straight-through processing, exception handling, and real-time transaction surveillance.</p>
            </div>
            <div class="hidden md:flex items-center gap-x-4 shrink-0">
              <div class="text-right">
                <div class="text-sm font-medium text-white">${this.user}</div>
                <div class="text-[11px] text-white/70">Fund Administrator • Operations</div>
              </div>
              <div class="corp-user-avatar w-9 h-9 rounded-full border-2 border-white/30" title=${this.user}>${this.userInitials()}</div>
            </div>
          </div>
        </div>
      </header>

      <div class="app-shell">
        <nav class="corp-sidebar flex flex-col shrink-0">
          <div class="px-3 pt-2 pb-4">
            <div class="section-label mb-2 px-3">Platform</div>
            ${TABS.map((t) => html`
              <div class="sidebar-item flex items-center gap-x-3 px-3 py-2 rounded mb-0.5 cursor-pointer ${this.tab === t.id ? 'active' : ''}"
                @click=${() => this.setTab(t.id)}>
                <i class="fa-solid ${t.icon} w-4"></i>
                <span class="text-sm font-medium">${t.label}</span>
                ${t.badge && (t.id === 'workbench' ? this.workbenchBadge : this.exceptionsBadge) > 0
                  ? html`<span class="nav-badge">${t.id === 'workbench' ? this.workbenchBadge : this.exceptionsBadge}</span>` : ''}
              </div>
            `)}
          </div>
        </nav>
        <main class="corp-main">${this.renderView()}</main>
      </div>

      <txn-modal></txn-modal>
      <review-workspace></review-workspace>
      <assistant-panel></assistant-panel>
      ${this.toast ? html`<div class="toast"><i class="fa-solid fa-check-circle"></i> ${this.toast}</div>` : ''}
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'agentx-app': AgentxApp; } }
