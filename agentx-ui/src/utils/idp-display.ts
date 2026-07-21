import { html, nothing, TemplateResult } from 'lit';
import { IDP_FIELDS, formatFieldLabel, formatFieldValue, heatClass } from '../constants/index.js';

type ExtractionEntry = { value?: unknown; confidence_score?: number };
type ExtractionResult = Record<string, ExtractionEntry | number | null | undefined>;
type IntakeLike = {
  extraction_result?: ExtractionResult | Record<string, unknown> | null;
  field_confidences?: Record<string, number>;
} | null | undefined;

const LEGACY_GOLDEN_KEYS: Record<string, string> = {
  party: 'investor_account_name',
  intent: 'transaction_type',
  currency: 'fund_currency',
  amount: 'amount_nominal',
  quantity: 'amount_unit',
  isin: 'fund_code',
  accountId: 'sa_reference_no',
  settlementDate: 'transaction_date',
};

const LEGACY_CONFIDENCE_KEYS: Record<string, string> = {
  ISIN: 'fund_code',
  Fund: 'fund_code',
  Investor: 'investor_account_name',
  Amount: 'amount_nominal',
  Date: 'transaction_date',
  Account: 'sa_reference_no',
  Currency: 'fund_currency',
  Quantity: 'amount_unit',
};

function applyLegacyGoldenKeys(schema: Record<string, unknown>): Record<string, unknown> {
  const normalized = { ...schema };
  for (const [oldKey, newKey] of Object.entries(LEGACY_GOLDEN_KEYS)) {
    const legacyValue = normalized[oldKey];
    const currentValue = normalized[newKey];
    if (legacyValue !== undefined && legacyValue !== null && legacyValue !== ''
      && (currentValue === undefined || currentValue === null || currentValue === '')) {
      normalized[newKey] = legacyValue;
    }
  }
  return normalized;
}

function applyLegacyConfidenceKeys(confidences: Record<string, number>): Record<string, number> {
  const normalized = { ...confidences };
  for (const [oldKey, newKey] of Object.entries(LEGACY_CONFIDENCE_KEYS)) {
    if (normalized[oldKey] !== undefined && normalized[newKey] === undefined) {
      normalized[newKey] = normalized[oldKey];
    }
  }
  return normalized;
}

function parseExtractionResult(extraction?: ExtractionResult | Record<string, unknown> | null): {
  values: Record<string, unknown>;
  confidences: Record<string, number>;
} {
  const values: Record<string, unknown> = {};
  const confidences: Record<string, number> = {};
  if (!extraction) return { values, confidences };

  for (const field of IDP_FIELDS) {
    const entry = extraction[field];
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) continue;
    const typed = entry as ExtractionEntry;
    values[field] = typed.value ?? null;
    if (typed.confidence_score !== undefined && typed.confidence_score !== null) {
      confidences[field] = Number(typed.confidence_score);
    }
  }
  return { values, confidences };
}

export function resolveGoldenSchema(
  schema?: Record<string, unknown> | null,
  intake?: IntakeLike,
): Record<string, unknown> {
  const resolved: Record<string, unknown> = {};
  const fromSchema = applyLegacyGoldenKeys(schema || {});
  const { values: fromExtraction } = parseExtractionResult(intake?.extraction_result);

  for (const field of IDP_FIELDS) {
    const direct = fromSchema[field];
    const extracted = fromExtraction[field];
    resolved[field] = direct !== undefined && direct !== null && direct !== ''
      ? direct
      : (extracted ?? null);
  }
  return resolved;
}

export function resolveFieldConfidences(
  confidences?: Record<string, number> | null,
  intake?: IntakeLike,
): Record<string, number> {
  const { confidences: fromExtraction } = parseExtractionResult(intake?.extraction_result);
  const merged = applyLegacyConfidenceKeys({
    ...fromExtraction,
    ...(intake?.field_confidences || {}),
    ...(confidences || {}),
  });

  const resolved: Record<string, number> = {};
  for (const field of IDP_FIELDS) {
    resolved[field] = merged[field] ?? 0;
  }
  return resolved;
}

export function renderGoldenSchemaTable(
  schema?: Record<string, unknown> | null,
  intake?: IntakeLike,
): TemplateResult {
  const resolved = resolveGoldenSchema(schema, intake);
  return html`
    <div class="golden-schema-table" style="display:grid;grid-template-columns:minmax(180px,1fr) 2fr;gap:8px 16px;font-size:12px;">
      ${IDP_FIELDS.map((field) => html`
        <div class="text-slate-500">${formatFieldLabel(field)}</div>
        <div class="font-medium text-gray-900">${formatFieldValue(resolved[field])}</div>
      `)}
    </div>
  `;
}

export function goldenSchemaToFormValues(
  schema?: Record<string, unknown> | null,
  intake?: IntakeLike,
): Record<string, string> {
  const resolved = resolveGoldenSchema(schema, intake);
  const form: Record<string, string> = {};
  for (const field of IDP_FIELDS) {
    const value = resolved[field];
    form[field] = value === null || value === undefined ? '' : String(value);
  }
  return form;
}

export function collectFieldCorrections(
  edited: Record<string, string>,
  original: Record<string, string>,
): Record<string, string> {
  const corrections: Record<string, string> = {};
  for (const field of IDP_FIELDS) {
    const editedVal = (edited[field] ?? '').trim();
    const originalVal = (original[field] ?? '').trim();
    if (editedVal !== originalVal) {
      corrections[field] = editedVal;
    }
  }
  return corrections;
}

export function renderEditableFieldsForm(
  values: Record<string, string>,
  confidences: Record<string, number>,
  onFieldChange: (field: string, value: string) => void,
  options: { disabled?: boolean } = {},
): TemplateResult {
  const disabled = options.disabled ?? false;
  return html`
    <div class="editable-fields-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px 16px;">
      ${IDP_FIELDS.map((field) => {
        const score = confidences[field] ?? 0;
        const needsReview = score > 0 && score < 98;
        return html`
          <div>
            <div class="field-label mb-1 flex items-center justify-between gap-2">
              <span>${formatFieldLabel(field)}</span>
              ${needsReview
                ? html`<span class="text-[10px] text-amber-600 whitespace-nowrap">${score}%</span>`
                : nothing}
            </div>
            <input
              type="text"
              class="editable-field w-full"
              style=${needsReview && !disabled ? 'border-color:#fcd34d;' : ''}
              .value=${values[field] ?? ''}
              ?disabled=${disabled}
              @input=${(e: Event) => onFieldChange(field, (e.target as HTMLInputElement).value)}
            />
          </div>
        `;
      })}
    </div>
  `;
}

export function renderConfidenceHeatmap(
  fields?: Record<string, number> | null,
  intake?: IntakeLike,
): TemplateResult {
  const resolved = resolveFieldConfidences(fields, intake);
  return html`
    <div class="heatmap-grid">
      ${IDP_FIELDS.map((field) => {
        const score = resolved[field] ?? 0;
        return html`
          <div class="heatmap-cell ${heatClass(score)}">
            ${formatFieldLabel(field)}<br><strong>${score}%</strong>
          </div>
        `;
      })}
    </div>
  `;
}
