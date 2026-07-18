import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { api } from '../../services/api-client.js';
import { ASSISTANT_QUERIES } from '../../constants/index.js';

const SUGGESTED_ACTIONS = [
  { query: ASSISTANT_QUERIES[0], icon: 'fa-clock', title: 'SLA status today', desc: 'Compliance rate and at-risk instructions', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[1], icon: 'fa-scale-balanced', title: 'Reconciliation exceptions', desc: 'Open mismatches and settlement gaps', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[3], icon: 'fa-chart-line', title: 'Journey bottleneck', desc: 'Stage performance and root causes', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[2], icon: 'fa-triangle-exclamation', title: 'High priority exceptions', desc: 'Items requiring immediate attention', bg: 'bg-red-50', color: 'text-red-500' },
];

@customElement('assistant-panel')
export class AssistantPanel extends LightDomElement {
  @state() private open = false;
  @state() private welcome: Awaited<ReturnType<typeof api.getAssistantWelcome>> | null = null;
  @state() private messages: { role: string; text: string; stats?: string[] }[] = [];
  @state() private input = '';
  @state() private typing = false;

  async connectedCallback() {
    super.connectedCallback();
    this.welcome = await api.getAssistantWelcome();
  }

  toggle() {
    this.open = !this.open;
  }

  private async send(msg?: string) {
    const text = msg || this.input.trim();
    if (!text) return;
    this.messages = [...this.messages, { role: 'user', text }];
    this.input = '';
    this.typing = true;
    const result = await api.chat(text);
    this.typing = false;
    this.messages = [...this.messages, { role: 'bot', text: result.reply_html, stats: result.meta?.stats }];
  }

  render() {
    return html`
      <div id="assistant-root" style="position:fixed;bottom:24px;right:24px;z-index:500;">
        ${this.open ? html`
          <div class="assistant-panel assistant-panel-enter" style="position:absolute;bottom:72px;right:0;width:400px;height:560px;display:flex;flex-direction:column;overflow:hidden;border-radius:16px;">
            <div class="assistant-header px-4 py-3 flex items-center justify-between shrink-0">
              <div class="flex items-center gap-3">
                <div class="relative">
                  <div class="assistant-avatar w-10 h-10 rounded-xl flex items-center justify-center" style="width:40px;height:40px;">
                    <i class="fa-solid fa-wand-magic-sparkles text-white text-sm"></i>
                  </div>
                  <span class="assistant-status-dot" style="position:absolute;bottom:-2px;right:-2px;width:12px;height:12px;background:#4ade80;border:2px solid #fff;border-radius:50%;"></span>
                </div>
                <div>
                  <div class="font-display text-base font-semibold tracking-tight text-white">AgentX Assistant</div>
                  <div class="text-[11px] text-blue-200 flex items-center gap-1.5">
                    <span style="width:6px;height:6px;background:#bfdbfe;border-radius:50%;display:inline-block;"></span>
                    Online • Operations Intelligence
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-1">
                <button class="w-8 h-8 rounded-lg text-white/70 flex items-center justify-center" style="border:none;background:none;cursor:pointer;" @click=${() => { this.open = false; }} title="Close">
                  <i class="fa-solid fa-xmark text-sm"></i>
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto px-4 py-4">
              ${this.messages.length === 0 ? html`
                <div class="space-y-4">
                  <div class="text-center py-2">
                    <div class="text-sm text-gray-700 font-medium">${this.welcome?.greeting || 'Good morning'}</div>
                    <div class="text-xs text-gray-500 mt-1">I have full visibility into today's transaction operations. How can I help?</div>
                  </div>
                  ${this.welcome ? html`
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
                      ${this.welcome.stats.map((s) => html`
                        <div class="assistant-stat-chip rounded-xl p-2.5 text-center">
                          <div class="text-lg font-semibold text-blue-600 kpi-value">${s.value}</div>
                          <div class="text-[9px] text-gray-500" style="text-transform:uppercase;letter-spacing:0.05em;">${s.label}</div>
                        </div>
                      `)}
                    </div>
                  ` : ''}
                  <div class="text-[10px] text-slate-500" style="text-transform:uppercase;letter-spacing:0.05em;font-weight:600;padding:0 4px;">Suggested actions</div>
                  <div class="space-y-2">
                    ${SUGGESTED_ACTIONS.map((a) => html`
                      <button class="assistant-welcome-card w-full text-left px-3.5 py-3 rounded-xl flex items-start gap-3" style="cursor:pointer;"
                        @click=${() => this.send(a.query)}>
                        <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style="background:${a.bg.includes('red') ? '#fef2f2' : '#eff6ff'};">
                          <i class="fa-solid ${a.icon} ${a.color} text-xs"></i>
                        </div>
                        <div>
                          <div class="text-sm font-medium text-gray-800">${a.title}</div>
                          <div class="text-[11px] text-gray-500 mt-0.5">${a.desc}</div>
                        </div>
                      </button>
                    `)}
                  </div>
                </div>
              ` : html`
                <div class="space-y-4">
                  ${this.messages.map((m) => html`
                    <div style="display:flex;${m.role === 'user' ? 'justify-content:flex-end;' : 'gap:10px;align-items:flex-start;'}">
                      ${m.role === 'bot' ? html`
                        <div class="assistant-avatar w-7 h-7 rounded-lg flex items-center justify-center shrink-0" style="width:28px;height:28px;">
                          <i class="fa-solid fa-wand-magic-sparkles text-white text-[10px]"></i>
                        </div>
                        <div class="assistant-msg-bot px-4 py-3 text-sm">${unsafeHTML(m.text)}</div>
                      ` : html`<div class="assistant-msg-user px-4 py-2.5 text-sm text-white">${m.text}</div>`}
                    </div>
                  `)}
                  ${this.typing ? html`
                    <div class="flex items-start gap-2.5">
                      <div class="assistant-avatar w-7 h-7 rounded-lg flex items-center justify-center shrink-0" style="width:28px;height:28px;">
                        <i class="fa-solid fa-wand-magic-sparkles text-white text-[10px]"></i>
                      </div>
                      <div class="assistant-msg-bot px-4 py-3 assistant-typing flex gap-1 items-center">
                        <span style="width:6px;height:6px;background:#94a3b8;border-radius:50%;"></span>
                        <span style="width:6px;height:6px;background:#94a3b8;border-radius:50%;"></span>
                        <span style="width:6px;height:6px;background:#94a3b8;border-radius:50%;"></span>
                      </div>
                    </div>
                  ` : ''}
                </div>
              `}
            </div>

            <div class="assistant-composer px-4 py-3 shrink-0">
              <div class="flex items-end gap-2">
                <textarea class="assistant-input flex-1 rounded-xl px-4 py-2.5 text-sm text-gray-800 resize-none"
                  rows="1" placeholder="Ask about transactions, exceptions, SLA..."
                  .value=${this.input}
                  @input=${(e: Event) => { this.input = (e.target as HTMLTextAreaElement).value; }}
                  @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); } }}></textarea>
                <button class="assistant-send-btn w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="border:none;cursor:pointer;" @click=${() => this.send()}>
                  <i class="fa-solid fa-paper-plane text-white text-sm"></i>
                </button>
              </div>
              <div class="flex items-center justify-between mt-2 px-1">
                <div class="text-[10px] text-slate-500 flex items-center gap-1">
                  <i class="fa-solid fa-shield-halved text-blue-600"></i>
                  <span>Enterprise data • Audited responses</span>
                </div>
                <span class="text-[10px] text-slate-600">↵ to send</span>
              </div>
            </div>
          </div>
        ` : ''}

        <button type="button" class="assistant-fab assistant-fab-pulse group relative w-14 h-14 rounded-2xl flex items-center justify-center" style="border:none;cursor:pointer;width:56px;height:56px;" @click=${() => this.toggle()} aria-label="Open AgentX Assistant">
          <i class="fa-solid fa-wand-magic-sparkles text-white text-xl"></i>
          <span style="position:absolute;right:100%;margin-right:12px;padding:6px 12px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;font-size:12px;font-weight:500;color:#374151;white-space:nowrap;opacity:0;transition:opacity 0.2s;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,0.1);"
            class="group-hover-show">AgentX Assistant</span>
        </button>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'assistant-panel': AssistantPanel; } }
