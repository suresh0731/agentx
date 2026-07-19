import { html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { LightDomElement } from '../../utils/light-dom.js';
import { JOURNEY_STEPS } from '../../constants/index.js';

export interface JourneyState {
  state?: string;
  completedThrough?: number;
  activeStep?: number;
  heldStep?: number;
  failedStep?: number;
}

@customElement('ax-step-tracker')
export class AxStepTracker extends LightDomElement {
  @property({ type: Object }) journey: JourneyState = {};
  @property() variant: 'default' | 'workspace' | 'card' = 'default';
  @property() context: 'queue' | 'workbench' = 'queue';

  private statusInfo() {
    const j = this.journey || {};
    const completedThrough = j.completedThrough || 0;
    const activeStep = j.activeStep || 0;
    const failedStep = j.failedStep || 0;
    const heldStep = j.heldStep || 0;

    if (j.state === 'completed' || completedThrough >= 6) {
      return { text: html`<i class="fa-solid fa-check-circle"></i> Complete`, cls: 'text-emerald-400' };
    }
    if (heldStep > 0) {
      const step = JOURNEY_STEPS[heldStep - 1];
      return {
        text: html`<i class="fa-solid ${step.icon}"></i> Awaiting review · <strong>${step.full}</strong>`,
        cls: 'text-amber-400',
      };
    }
    if (failedStep > 0) {
      const step = JOURNEY_STEPS[failedStep - 1];
      return {
        text: this.context === 'workbench'
          ? html`<i class="fa-solid ${step.icon}"></i> Exception · <strong>${step.full}</strong>`
          : html`<i class="fa-solid ${step.icon}"></i> Failed at <strong>${step.full}</strong>`,
        cls: 'text-red-400',
      };
    }
    if (activeStep > 0) {
      const step = JOURNEY_STEPS[activeStep - 1];
      return {
        text: html`<i class="fa-solid ${step.icon}"></i> Processing · <strong>${step.full}</strong>`,
        cls: 'text-emerald-400',
      };
    }
    return { text: '', cls: 'text-slate-400' };
  }

  render() {
    const j = this.journey || {};
    const completedThrough = j.completedThrough || 0;
    const activeStep = j.activeStep || 0;
    const failedStep = j.failedStep || 0;
    const heldStep = j.heldStep || 0;
    const isComplete = j.state === 'completed' || completedThrough >= 6;
    const status = this.statusInfo();
    const trackerClass = this.variant === 'workspace'
      ? 'step-tracker step-tracker-workspace'
      : this.variant === 'card' ? 'step-tracker step-tracker-card' : 'step-tracker';

    return html`
      <div class="${trackerClass}">
        ${status.text ? html`<div class="step-tracker-status ${status.cls}">${status.text}</div>` : ''}
        <div class="step-track">
          ${JOURNEY_STEPS.map((step, i) => {
            const stepNum = i + 1;
            let nodeClass = 'step-node step-pending';
            let wrapClass = 'step-node-wrap';
            let labelClass = 'step-label';
            let failBadge = html``;

            if (failedStep === stepNum) {
              nodeClass = 'step-node step-failed';
              wrapClass += ' step-failed';
              labelClass += ' step-label-failed';
              failBadge = html`<span class="step-fail-badge"><i class="fa-solid fa-xmark"></i></span>`;
            } else if (heldStep === stepNum) {
              nodeClass = 'step-node step-held';
              wrapClass += ' step-held';
              labelClass += ' step-label-held';
            } else if (isComplete || stepNum <= completedThrough) {
              nodeClass = 'step-node step-done';
              wrapClass += ' step-done';
              labelClass += ' step-label-done';
            } else if (activeStep === stepNum) {
              nodeClass = 'step-node step-processing';
              wrapClass += ' step-processing';
              labelClass += ' step-label-processing';
            }

            return html`
              <div class="${wrapClass}" title=${step.full}>
                ${failBadge}
                <div class="${nodeClass}"><i class="fa-solid ${step.icon}"></i></div>
                <div class="${labelClass}">${step.short}</div>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ax-step-tracker': AxStepTracker;
  }
}
