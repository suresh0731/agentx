const BASE = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  getMe: () => request<{ display_name: string }>('/me'),
  getKpis: () => request<{ primary: KpiTile[]; secondary: KpiTile[] }>('/dashboard/kpis'),
  getJourneyHealth: () => request<JourneyHealth>('/dashboard/journey-health'),
  getOpsMetrics: () => request<{ metrics: OpsMetric[] }>('/dashboard/ops-metrics'),
  getAttention: () => request<Attention>('/dashboard/attention'),
  getChannels: () => request<ChannelStat[]>('/dashboard/channels'),
  getRouting: () => request<{ ta: number; fa: number; is: number }>('/dashboard/routing'),
  getIntents: () => request<IntentStat[]>('/dashboard/intents'),
  getInstructions: () => request<InstructionSummary[]>('/instructions'),
  getExceptions: () => request<ExceptionSummary[]>('/exceptions'),
  getInstruction: (id: string) => request<InstructionDetail>(`/instructions/${id}`),
  updateInstructionFields: (id: string, body: { fields: Record<string, string>; note?: string }) =>
    request<InstructionDetail>(`/instructions/${id}/fields`, { method: 'PATCH', body: JSON.stringify(body) }),
  approveInstruction: (id: string, body: { fields?: Record<string, string>; note?: string } = {}) =>
    request(`/instructions/${id}/approve`, { method: 'POST', body: JSON.stringify(body) }),
  getWorkbench: () => request<WorkbenchCard[]>('/workbench/requests'),
  getWorkbenchDetail: (id: string) => request<WorkbenchCard>(`/workbench/requests/${id}`),
  patchWorkbenchStage: (id: string, stage: string) =>
    request(`/workbench/requests/${id}/stage`, { method: 'PATCH', body: JSON.stringify({ stage }) }),
  addComment: (id: string, comment: { user: string; text: string; time: string }) =>
    request(`/workbench/requests/${id}/comments`, { method: 'POST', body: JSON.stringify(comment) }),
  getInsights: () => request<WorkbenchInsights>('/workbench/insights'),
  getAudit: () => request<AuditEvent[]>('/audit'),
  getConfigRules: () => request<{ validation: string[]; repair: string[] }>('/config/rules'),
  getAssistantWelcome: () => request<{ greeting: string; stats: { label: string; value: string }[] }>('/assistant/welcome'),
  chat: async (message: string): Promise<{ reply_html: string; meta?: { stats: string[] } }> => {
    const res = await fetch(`${BASE}/assistant/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const text = await res.text();
    const lines = text.split('\n');
    let reply = '';
    let stats: string[] = [];
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (line.includes('meta')) {
          try { stats = JSON.parse(data.replace(/'/g, '"')).stats || []; } catch { /* ignore */ }
        } else {
          reply = data;
        }
      }
    }
    return { reply_html: reply || text, meta: { stats } };
  },
};

export interface KpiTile {
  key: string; label: string; value: number; unit?: string;
  delta?: number; delta_label?: string; footnote?: string; tone?: string;
}
export interface OpsMetric {
  key: string; label: string; value: number; unit?: string;
  footnote?: string; tone?: string; icon?: string;
}
export interface JourneyHealth {
  overall_stp: number; stages: { stage: number; label: string; pass_rate: number; is_bottleneck?: boolean }[];
}
export interface Attention { total: number; high_priority: number; sla_at_risk: number; recon_mismatches: number; aml_holds: number; }
export interface ChannelStat { name: string; volume: number; stp_rate: number; icon?: string; }
export interface IntentStat { intent: string; stp_rate: number; }
export interface Journey { state?: string; completedThrough?: number; activeStep?: number; heldStep?: number; failedStep?: number; }
export interface InstructionSummary {
  ref: string; filename: string; source: string; intent: string; dest: string; conf: string; confValue: number; status: string; journey: Journey;
}
export interface ExceptionSummary { ref: string; filename: string; issue: string; failed_step: number; priority: string; journey: Journey; }
export interface InstructionDetail {
  ref: string; meta?: string; stage_label?: string; confidence: number; golden_schema?: Record<string, unknown>;
  intake?: { extraction_result?: Record<string, unknown>; field_confidences?: Record<string, number> };
  party?: string; account?: string; settlement?: string; amount?: string; units?: string;
  decisions?: string[]; repair_notes?: string[]; field_confidences?: Record<string, number>;
  timeline?: object[]; journey: Journey; recon_status?: string; recon_detail?: string;
}
export interface WorkbenchCard {
  id: string; ref: string; stage: string; intent: string; source: string; party: string; amount: string;
  confidence: number; risk: number; riskLabel: string; slaMinutes: number; slaRemaining: number;
  assignee: string; journey: Journey; fields: Record<string, number>;
  golden_schema?: Record<string, unknown>;
  intake?: { extraction_result?: Record<string, unknown>; field_confidences?: Record<string, number> };
  findings: string[]; explain: string; timeline: string[]; comments: { user: string; text: string; time: string }[];
}
export interface WorkbenchInsights {
  total: number; in_review: number; sla_at_risk: number; sla_breached: number;
  avg_confidence: number; distribution: Record<string, number>; paths_today: Record<string, number>;
}
export interface AuditEvent {
  id: string; instruction_id: string; timestamp: string; summary: string; detail?: string; actor: string;
}
