export const JOURNEY_STEPS = [
  { short: 'Ingest', full: 'Ingestion', icon: 'fa-inbox' },
  { short: 'Detect', full: 'Detect & Classify', icon: 'fa-search' },
  { short: 'Validate', full: 'Validate & Enrich', icon: 'fa-check-double' },
  { short: 'Repair', full: 'Repair + Templatise', icon: 'fa-tools' },
  { short: 'Route', full: 'Routing', icon: 'fa-share' },
  { short: 'Reconcile', full: 'Reconciliation', icon: 'fa-scale-balanced' },
];

export const WORKBENCH_STAGES = [
  { id: 'submitted', label: 'Submitted', icon: 'fa-inbox', color: '#60a5fa' },
  { id: 'validation', label: 'AI Validation', icon: 'fa-robot', color: '#a78bfa' },
  { id: 'review', label: 'Human Review', icon: 'fa-user-check', color: '#fbbf24' },
  { id: 'approved', label: 'Approved', icon: 'fa-circle-check', color: '#34d399' },
  { id: 'rejected', label: 'Rejected', icon: 'fa-circle-xmark', color: '#f87171' },
  { id: 'escalated', label: 'Escalated', icon: 'fa-arrow-up-right-dots', color: '#f472b6' },
];

export const ASSISTANT_QUERIES = [
  "What's our SLA compliance today?",
  'Show reconciliation exceptions',
  'List high priority exceptions',
  'Which stage is the bottleneck?',
];

export function confClass(v: number): string {
  if (v >= 95) return 'conf-fill-high';
  if (v >= 80) return 'conf-fill-med';
  return 'conf-fill-low';
}

export function slaClass(mins: number): string {
  if (mins <= 0) return 'sla-critical';
  if (mins <= 15) return 'sla-warn';
  return 'sla-ok';
}

export function formatSla(mins: number): string {
  if (mins <= 0) return `SLA breached ${Math.abs(mins)}m ago`;
  if (mins < 60) return `${mins}m left`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m left`;
}

export function riskColor(risk: number): string {
  if (risk >= 70) return '#f87171';
  if (risk >= 40) return '#fbbf24';
  return '#34d399';
}
