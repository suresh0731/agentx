import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ax-kpi-tile')
export class AxKpiTile extends LitElement {
  @property() label = '';
  @property() value: string | number = '';
  @property() unit = '';
  @property() footnote = '';
  @property() delta = '';
  @property() tone = 'neutral';

  static styles = css`
  .tile { padding: 20px; border-radius: 16px; }
  .label { font-size: 11px; color: var(--corp-text-muted); margin-bottom: 8px; }
  .value { font-size: 28px; font-weight: 600; }
  .footnote { font-size: 11px; color: var(--corp-text-secondary); margin-top: 6px; }
  .success .value { color: var(--corp-success); }
  .warning .value { color: var(--corp-warning); }
  .danger .value { color: var(--corp-danger); }
  `;

  render() {
    return html`
      <div class="tile wireframe-card ${this.tone}">
        <div class="label">${this.label}</div>
        <div class="value kpi-value">${this.value}${this.unit}</div>
        ${this.footnote ? html`<div class="footnote">${this.footnote}</div>` : ''}
        ${this.delta ? html`<div class="footnote">${this.delta}</div>` : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap { 'ax-kpi-tile': AxKpiTile; }
}
