import { html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { LightDomElement } from '../utils/light-dom.js';
import { api } from '../services/api-client.js';

@customElement('configuration-view')
export class ConfigurationView extends LightDomElement {
  @state() private rules: { validation: string[]; repair: string[] } | null = null;

  async connectedCallback() {
    super.connectedCallback();
    this.rules = await api.getConfigRules();
  }

  render() {
    if (!this.rules) return html`<p class="text-sm text-slate-400">Loading...</p>`;
    return html`
      <h1 class="page-title mb-1">Configuration</h1>
      <p class="text-slate-400 mb-6">Rules applied by AgentX during validation, repair and templatisation</p>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div class="wireframe-card rounded-3xl p-6">
          <div class="font-semibold mb-4">Validation Rules</div>
          <div class="space-y-3 text-sm">
            ${this.rules.validation.map((r) => html`<div>${r}</div>`)}
          </div>
        </div>
        <div class="wireframe-card rounded-3xl p-6">
          <div class="font-semibold mb-4">Repair & Templatise Rules</div>
          <div class="space-y-3 text-sm">
            ${this.rules.repair.map((r) => html`<div>${r}</div>`)}
          </div>
        </div>
      </div>
    `;
  }
}

declare global { interface HTMLElementTagNameMap { 'configuration-view': ConfigurationView; } }
