import { html, nothing } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { api } from '../../services/api-client.js';
import { ASSISTANT_QUERIES } from '../../constants/index.js';

type ChatMessage = {
  role: 'user' | 'bot';
  text: string;
  stats?: string[];
  time?: string;
};

const SUGGESTED_ACTIONS = [
  { query: ASSISTANT_QUERIES[0], icon: 'fa-clock', title: 'SLA status today', desc: 'Compliance rate and at-risk instructions', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[1], icon: 'fa-scale-balanced', title: 'Reconciliation exceptions', desc: 'Open mismatches and settlement gaps', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[3], icon: 'fa-chart-line', title: 'Journey bottleneck', desc: 'Stage performance and root causes', bg: 'bg-blue-50', color: 'text-blue-600' },
  { query: ASSISTANT_QUERIES[2], icon: 'fa-triangle-exclamation', title: 'High priority exceptions', desc: '12 items requiring immediate attention', bg: 'bg-red-50', color: 'text-red-500' },
];

function statValueClass(label: string) {
  return label.toLowerCase().includes('exception') ? 'text-amber-400' : 'text-blue-600';
}

function statLabelClass(label: string) {
  return label.toLowerCase().includes('exception') ? 'text-slate-400' : 'text-gray-500';
}

const EXAMINING_STEPS = [
  'Understanding your question…',
  'Querying live ops data…',
  'Analysing results…',
];

const MIN_EXAMINING_MS = 900;
const EXAMINING_STEP_MS = 300;

function delay(ms: number) {
  return new Promise<void>((resolve) => { window.setTimeout(resolve, ms); });
}

@customElement('assistant-panel')
export class AssistantPanel extends LightDomElement {
  @state() private open = false;
  @state() private welcome: Awaited<ReturnType<typeof api.getAssistantWelcome>> | null = null;
  @state() private messages: ChatMessage[] = [];
  @state() private input = '';
  @state() private examining = false;
  @state() private examiningStep = 0;

  @query('#chat-messages-scroll') private scrollEl?: HTMLElement;

  private examiningTimer?: number;

  async connectedCallback() {
    super.connectedCallback();
    this.welcome = await api.getAssistantWelcome();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.clearExaminingTimer();
  }

  updated(changed: Map<string, unknown>) {
    super.updated(changed);
    if (changed.has('messages') || changed.has('examining') || changed.has('examiningStep')) {
      this.scrollToBottom();
    }
  }

  toggle() {
    this.open = !this.open;
  }

  private minimize() {
    this.open = false;
  }

  private clearExaminingTimer() {
    if (this.examiningTimer !== undefined) {
      window.clearInterval(this.examiningTimer);
      this.examiningTimer = undefined;
    }
  }

  private startExamining() {
    this.examining = true;
    this.examiningStep = 0;
    this.clearExaminingTimer();
    this.examiningTimer = window.setInterval(() => {
      if (this.examiningStep < EXAMINING_STEPS.length - 1) {
        this.examiningStep += 1;
      }
    }, EXAMINING_STEP_MS);
  }

  private stopExamining() {
    this.clearExaminingTimer();
    this.examining = false;
    this.examiningStep = 0;
  }

  private scrollToBottom() {
    requestAnimationFrame(() => {
      if (this.scrollEl) this.scrollEl.scrollTop = this.scrollEl.scrollHeight;
    });
  }

  private async send(msg?: string) {
    const text = msg || this.input.trim();
    if (!text || this.examining) return;
    this.messages = [...this.messages, { role: 'user', text }];
    this.input = '';
    this.startExamining();
    const [result] = await Promise.all([
      api.chat(text),
      delay(MIN_EXAMINING_MS),
    ]);
    this.stopExamining();
    this.messages = [
      ...this.messages,
      {
        role: 'bot',
        text: result.reply_html,
        stats: result.meta?.stats,
        time: 'Just now',
      },
    ];
  }

  private renderWelcome() {
    return html`
      <div id="chat-welcome" class="space-y-4">
        <div class="text-center py-2">
          <div class="text-sm text-gray-700 font-medium">${this.welcome?.greeting || 'Good morning'}</div>
          <div class="text-xs text-gray-500 mt-1">I have full visibility into today's transaction operations. How can I help?</div>
        </div>
        ${this.welcome ? html`
          <div class="grid grid-cols-3 gap-2">
            ${this.welcome.stats.map((s) => html`
              <div class="assistant-stat-chip rounded-xl p-2.5 text-center">
                <div class="text-lg font-semibold kpi-value ${statValueClass(s.label)}">${s.value}</div>
                <div class="text-[9px] ${statLabelClass(s.label)} uppercase tracking-wide">${s.label}</div>
              </div>
            `)}
          </div>
        ` : nothing}
        <div class="text-[10px] text-slate-500 uppercase tracking-wider font-semibold px-1">Suggested actions</div>
        <div class="space-y-2">
          ${SUGGESTED_ACTIONS.map((a) => html`
            <button type="button" class="assistant-welcome-card w-full text-left px-3.5 py-3 rounded-xl flex items-start gap-3"
              @click=${() => this.send(a.query)}>
              <div class="w-8 h-8 rounded-lg ${a.bg} flex items-center justify-center shrink-0 mt-0.5">
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
    `;
  }

  private renderMessages() {
    return html`
      <div id="chat-messages" class="space-y-4">
        ${this.messages.map((m) => html`
          ${m.role === 'user' ? html`
            <div class="flex justify-end">
              <div class="assistant-msg-user text-white text-sm px-4 py-2.5 max-w-[85%] leading-relaxed">${m.text}</div>
            </div>
          ` : html`
            <div class="flex items-start gap-2.5 assistant-msg-enter">
              <div class="assistant-avatar w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                <i class="fa-solid fa-wand-magic-sparkles text-white text-[10px]"></i>
              </div>
              <div class="assistant-msg-bot text-sm text-slate-300 px-4 py-3 max-w-[90%] leading-relaxed">
                ${unsafeHTML(m.text)}
                ${m.stats?.length ? html`
                  <div class="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-slate-700/50">
                    ${m.stats.map((s) => html`
                      <span class="assistant-stat-chip text-[10px] px-2 py-1 rounded-lg text-emerald-400 font-medium">${s}</span>
                    `)}
                  </div>
                  <div class="text-[10px] text-slate-500 mt-2 flex items-center gap-1">
                    <i class="fa-solid fa-database text-emerald-500"></i>
                    <span>Sourced from live ops data • ${m.time || 'Just now'}</span>
                  </div>
                ` : nothing}
              </div>
            </div>
          `}
        `)}
      </div>
    `;
  }

  render() {
    const inConversation = this.messages.length > 0;

    return html`
      <div id="assistant-root" class="fixed bottom-6 right-6 z-[500]">
        ${this.open ? html`
          <div id="chat-window" class="assistant-panel assistant-panel-enter absolute bottom-[4.5rem] right-0 rounded-2xl w-[400px] h-[560px] flex flex-col overflow-hidden">
            <div class="assistant-header px-4 py-3.5 flex items-center justify-between shrink-0">
              <div class="flex items-center gap-3">
                <div class="relative">
                  <div class="assistant-avatar w-10 h-10 rounded-xl flex items-center justify-center">
                    <i class="fa-solid fa-wand-magic-sparkles text-white text-sm"></i>
                  </div>
                  <span class="assistant-status-dot absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 border-2 border-white rounded-full"></span>
                </div>
                <div>
                  <div class="font-display text-base font-semibold tracking-tight text-white">AgentX Assistant</div>
                  ${this.examining ? html`
                    <div class="text-[11px] text-amber-400 flex items-center gap-1.5">
                      <span class="w-1.5 h-1.5 bg-amber-400 rounded-full assistant-status-dot"></span>
                      Examining your question…
                    </div>
                  ` : html`
                    <div class="text-[11px] text-blue-200 flex items-center gap-1.5">
                      <span class="w-1.5 h-1.5 bg-blue-200 rounded-full"></span>
                      Online &bull; Operations Intelligence
                    </div>
                  `}
                </div>
              </div>
              <div class="flex items-center gap-1">
                <button type="button" class="assistant-header-btn" title="Minimize" @click=${() => this.minimize()}>
                  <i class="fa-solid fa-minus text-xs"></i>
                </button>
                <button type="button" class="assistant-header-btn" title="Close" @click=${() => { this.open = false; }}>
                  <i class="fa-solid fa-xmark text-sm"></i>
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto px-4 py-4" id="chat-messages-scroll">
              ${inConversation ? nothing : this.renderWelcome()}
              ${inConversation ? this.renderMessages() : nothing}
              ${this.examining ? html`
                <div id="chat-typing" class="mt-4 flex items-start gap-2.5">
                  <div class="assistant-avatar w-7 h-7 rounded-lg flex items-center justify-center shrink-0">
                    <i class="fa-solid fa-wand-magic-sparkles text-white text-[10px]"></i>
                  </div>
                  <div class="assistant-msg-bot px-4 py-3 max-w-[90%]">
                    <div class="assistant-examining-text">
                      <i class="fa-solid fa-magnifying-glass"></i>
                      <span>${EXAMINING_STEPS[this.examiningStep]}</span>
                    </div>
                    <div class="assistant-typing flex gap-1 items-center">
                      <span class="w-1.5 h-1.5 bg-slate-400 rounded-full"></span>
                      <span class="w-1.5 h-1.5 bg-slate-400 rounded-full"></span>
                      <span class="w-1.5 h-1.5 bg-slate-400 rounded-full"></span>
                    </div>
                  </div>
                </div>
              ` : nothing}
            </div>

            <div class="assistant-composer px-4 py-3 shrink-0">
              <div class="flex items-end gap-2">
                <div class="flex-1 relative">
                  <textarea id="chat-input" rows="1"
                    class="assistant-input w-full rounded-xl px-4 py-2.5 text-sm text-gray-800 resize-none max-h-24"
                    placeholder="Ask about transactions, exceptions, SLA..."
                    ?disabled=${this.examining}
                    .value=${this.input}
                    @input=${(e: Event) => { this.input = (e.target as HTMLTextAreaElement).value; }}
                    @keydown=${(e: KeyboardEvent) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); } }}></textarea>
                </div>
                <button type="button" class="assistant-send-btn w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  ?disabled=${this.examining}
                  @click=${() => this.send()}>
                  <i class="fa-solid fa-paper-plane text-white text-sm"></i>
                </button>
              </div>
              <div class="flex items-center justify-between mt-2 px-1">
                <div class="text-[10px] text-slate-500 flex items-center gap-1">
                  <i class="fa-solid fa-shield-halved text-blue-600"></i>
                  <span>Enterprise data &bull; Audited responses</span>
                </div>
                <span class="text-[10px] text-slate-600">↵ to send</span>
              </div>
            </div>
          </div>
        ` : nothing}

        <button id="assistant-fab" type="button"
          class="assistant-fab assistant-fab-pulse group relative w-14 h-14 rounded-2xl flex items-center justify-center"
          @click=${() => this.toggle()} aria-label="Open AgentX Assistant">
          <i id="assistant-fab-icon" class="fa-solid ${this.open ? 'fa-chevron-down text-lg' : 'fa-wand-magic-sparkles text-xl'} text-white"></i>
          <span class="assistant-fab-tooltip">AgentX Assistant</span>
          ${!this.open ? html`
            <span id="assistant-badge" class="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-amber-950 text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-white">3</span>
          ` : nothing}
        </button>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'assistant-panel': AssistantPanel; } }
