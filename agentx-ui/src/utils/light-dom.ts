import { LitElement } from 'lit';

/** Renders in light DOM so global enterprise styles apply (matches wireframe HTML). */
export class LightDomElement extends LitElement {
  protected createRenderRoot() {
    return this;
  }
}
