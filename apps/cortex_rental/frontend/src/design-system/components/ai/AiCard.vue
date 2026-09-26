<script setup lang="ts">
import { computed } from 'vue';
import { aiStateTokens, type AiStateType } from '../../tokens/colors';
import CortexIcon from '../../icons/CortexIcon.vue';
import AiStatusBadge from './AiStatusBadge.vue';

export interface EvidenceInfo {
  documentId?: string;
  documentName?: string;
  excerpt?: string;
  pageNumber?: number;
  sha256Hash?: string;
}

export interface PolicyBlockInfo {
  ruleCode: string;
  ruleName: string;
  explanation: string;
  remediationStep?: string;
}

export interface AuditExecutionInfo {
  auditEventId: string;
  actorName: string;
  executedAt: string;
  auditLink?: string;
}

interface Props {
  state: AiStateType;
  title: string;
  description?: string;
  locale?: 'fr-CA' | 'en-CA';
  isDemo?: boolean;
  confidence?: number;
  source?: string;
  timestamp?: string;
  evidence?: EvidenceInfo;
  policyBlock?: PolicyBlockInfo;
  auditExecution?: AuditExecutionInfo;
  needsConfirmationReason?: string;
  missingFields?: string[];
  approvalRequestId?: string;
  approvalRiskLevel?: 'low' | 'medium' | 'high';
  canApprove?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  locale: 'fr-CA',
  isDemo: false,
  description: undefined,
  confidence: undefined,
  source: undefined,
  timestamp: undefined,
  evidence: undefined,
  policyBlock: undefined,
  auditExecution: undefined,
  needsConfirmationReason: undefined,
  missingFields: () => [],
  approvalRequestId: undefined,
  approvalRiskLevel: 'medium',
  canApprove: true,
});

const emit = defineEmits<{
  (e: 'view-proof', evidence: EvidenceInfo | undefined): void;
  (e: 'edit'): void;
  (e: 'submit-approval', id?: string): void;
  (e: 'reject', reason?: string): void;
  (e: 'remediate'): void;
  (e: 'view-audit', auditId: string): void;
}>();

const config = computed(() => aiStateTokens[props.state] || aiStateTokens.verified);

const isFr = computed(() => props.locale === 'fr-CA');

const noOpBannerText = computed(() => {
  return isFr.value
    ? "Aucune action n'a été exécutée. Proposition IA préparée sans mutation métier."
    : "No action has been executed. AI proposal prepared without business mutation.";
});

const proofButtonText = computed(() => {
  return isFr.value ? "Voir la preuve source (1-clic)" : "View source evidence (1-click)";
});

const missingFieldsLabel = computed(() => {
  return isFr.value ? "Champs manquants / ambigus :" : "Missing / ambiguous fields:";
});

const policyBlockedLabel = computed(() => {
  return isFr.value ? "Règle de blocage :" : "Blocking rule:";
});

const nextStepLabel = computed(() => {
  return isFr.value ? "Prochaine étape autorisée :" : "Authorized next step:";
});

function handleViewProof() {
  emit('view-proof', props.evidence);
}

function handleViewAudit() {
  if (props.auditExecution?.auditEventId) {
    emit('view-audit', props.auditExecution.auditEventId);
  }
}
</script>

<template>
  <div
    :class="[
      'cx-ai-card',
      `cx-ai-card--${state}`,
      { 'cx-ai-card--proposed': state === 'proposed' },
    ]"
    :style="{
      borderColor: config.border,
      borderStyle: config.borderStyle,
      backgroundColor: state === 'proposed' ? 'var(--cortex-green-50, #edfbf2)' : 'var(--cortex-surface, #ffffff)',
    }"
    role="region"
    :aria-label="title"
  >
    <!-- Card Header -->
    <header class="cx-ai-card__header">
      <div class="cx-ai-card__title-group">
        <h3 class="cx-ai-card__title">{{ title }}</h3>
        <AiStatusBadge
          :state="state"
          :locale="locale"
          :is-demo="isDemo"
          :confidence="confidence"
          size="sm"
        />
      </div>

      <!-- Source / Timestamp (for Verified & Extracted) -->
      <div v-if="source || timestamp" class="cx-ai-card__meta">
        <span v-if="source" class="cx-ai-card__source">
          <CortexIcon name="cpu" :size="12" /> {{ source }}
        </span>
        <span v-if="timestamp" class="cx-ai-card__timestamp">
          {{ timestamp }}
        </span>
      </div>
    </header>

    <!-- PROPOSED STATE: Mandatory No-Op Notice Banner -->
    <div v-if="state === 'proposed'" class="cx-ai-card__noop-banner" role="note">
      <CortexIcon name="info" :size="14" color="var(--cortex-green-800, #044727)" />
      <span>{{ noOpBannerText }}</span>
    </div>

    <!-- Card Body Content -->
    <div class="cx-ai-card__body">
      <p v-if="description" class="cx-ai-card__description">
        {{ description }}
      </p>

      <slot />

      <!-- EXTRACTED STATE: 1-Click Evidence / Proof Box -->
      <div v-if="state === 'extracted' && evidence" class="cx-ai-card__evidence-box">
        <div class="cx-ai-card__evidence-header">
          <span class="cx-ai-card__evidence-doc">
            <CortexIcon name="file-text" :size="13" color="var(--cortex-violet-800, #5b21b6)" />
            <strong>{{ evidence.documentName || evidence.documentId }}</strong>
            <span v-if="evidence.pageNumber"> (p. {{ evidence.pageNumber }})</span>
          </span>
          <button
            type="button"
            class="cx-ai-card__proof-btn"
            @click="handleViewProof"
          >
            <CortexIcon name="external-link" :size="12" />
            {{ proofButtonText }}
          </button>
        </div>

        <blockquote v-if="evidence.excerpt" class="cx-ai-card__evidence-quote">
          « {{ evidence.excerpt }} »
        </blockquote>

        <div v-if="evidence.sha256Hash" class="cx-ai-card__hash">
          SHA-256: <code>{{ evidence.sha256Hash }}</code>
        </div>
      </div>

      <!-- NEEDS_CONFIRMATION STATE: Missing Fields & Ambiguity -->
      <div v-if="state === 'needs_confirmation'" class="cx-ai-card__confirmation-box">
        <div v-if="needsConfirmationReason" class="cx-ai-card__reason">
          <CortexIcon name="alert-triangle" :size="14" color="var(--cortex-amber-900, #78350f)" />
          <span>{{ needsConfirmationReason }}</span>
        </div>

        <div v-if="missingFields && missingFields.length > 0" class="cx-ai-card__missing-fields">
          <span class="cx-ai-card__missing-label">{{ missingFieldsLabel }}</span>
          <ul class="cx-ai-card__missing-list">
            <li v-for="field in missingFields" :key="field" class="cx-ai-card__missing-item">
              <code>{{ field }}</code>
            </li>
          </ul>
        </div>
      </div>

      <!-- APPROVAL_REQUIRED STATE: SAS Gate Notice -->
      <div v-if="state === 'approval_required'" class="cx-ai-card__approval-box">
        <div class="cx-ai-card__approval-notice">
          <CortexIcon name="lock" :size="16" color="var(--cortex-amber-900, #78350f)" />
          <div>
            <strong>{{ isFr ? "Action bloquée en attente de superviseur" : "Action locked pending supervisor approval" }}</strong>
            <p>{{ isFr ? "Conformément à la politique d'autonomie supervisée, un agent ne peut pas auto-approuver cette mutation." : "In compliance with supervised autonomy policy, an agent cannot self-approve this mutation." }}</p>
          </div>
        </div>
      </div>

      <!-- APPROVED_EXECUTED STATE: Audit Traceability Box -->
      <div v-if="state === 'approved_executed' && auditExecution" class="cx-ai-card__audit-box">
        <div class="cx-ai-card__audit-row">
          <span class="cx-ai-card__audit-item">
            <CortexIcon name="shield-check" :size="14" color="var(--cortex-green-800, #044727)" />
            <span>Audit ID: <strong class="cx-ai-card__audit-id">{{ auditExecution.auditEventId }}</strong></span>
          </span>
          <span class="cx-ai-card__audit-item">
            <span>{{ isFr ? "Approuvé par :" : "Approved by:" }} <strong>{{ auditExecution.actorName }}</strong></span>
          </span>
          <span class="cx-ai-card__audit-item">
            <span>{{ auditExecution.executedAt }}</span>
          </span>
        </div>
        <button
          v-if="auditExecution.auditEventId"
          type="button"
          class="cx-ai-card__audit-link-btn"
          @click="handleViewAudit"
        >
          <CortexIcon name="external-link" :size="12" />
          {{ isFr ? "Consulter l'événement dans le journal d'audit" : "View event in immutable audit log" }}
        </button>
      </div>

      <!-- BLOCKED_BY_POLICY STATE: Rule Code & Next Step -->
      <div v-if="state === 'blocked_by_policy' && policyBlock" class="cx-ai-card__policy-box">
        <div class="cx-ai-card__policy-rule">
          <CortexIcon name="shield-x" :size="16" color="var(--cortex-red-900, #7f1d1d)" />
          <div>
            <div class="cx-ai-card__policy-code">
              {{ policyBlockedLabel }} <strong>{{ policyBlock.ruleCode }}</strong> — {{ policyBlock.ruleName }}
            </div>
            <p class="cx-ai-card__policy-desc">{{ policyBlock.explanation }}</p>
          </div>
        </div>

        <div v-if="policyBlock.remediationStep" class="cx-ai-card__policy-remediation">
          <span class="cx-ai-card__next-label">{{ nextStepLabel }}</span>
          <p class="cx-ai-card__next-text">{{ policyBlock.remediationStep }}</p>
        </div>
      </div>
    </div>

    <!-- Card Footer / Actions -->
    <footer v-if="$slots.actions || state === 'proposed' || state === 'approval_required' || state === 'blocked_by_policy'" class="cx-ai-card__footer">
      <slot name="actions">
        <!-- Default Actions for Proposed -->
        <template v-if="state === 'proposed'">
          <button
            type="button"
            class="cx-ai-btn cx-ai-btn--secondary"
            @click="emit('edit')"
          >
            {{ isFr ? "Éditer dans le Composer" : "Edit in Composer" }}
          </button>
          <button
            type="button"
            class="cx-ai-btn cx-ai-btn--primary"
            @click="emit('submit-approval', approvalRequestId)"
          >
            {{ isFr ? "Soumettre pour validation" : "Submit for Approval" }}
          </button>
          <button
            type="button"
            class="cx-ai-btn cx-ai-btn--danger-ghost"
            @click="emit('reject')"
          >
            {{ isFr ? "Rejeter avec motif" : "Reject with reason" }}
          </button>
        </template>

        <!-- Default Actions for Approval Required -->
        <template v-else-if="state === 'approval_required'">
          <button
            type="button"
            class="cx-ai-btn cx-ai-btn--warning"
            @click="emit('submit-approval', approvalRequestId)"
          >
            <CortexIcon name="lock" :size="13" />
            {{ isFr ? "Ouvrir dans la file d'approbation (SAS)" : "Open in Approval Queue" }}
          </button>
        </template>

        <!-- Default Actions for Policy Blocked -->
        <template v-else-if="state === 'blocked_by_policy'">
          <button
            type="button"
            class="cx-ai-btn cx-ai-btn--secondary"
            @click="emit('remediate')"
          >
            {{ isFr ? "Appliquer la remédiation" : "Apply Remediation" }}
          </button>
        </template>
      </slot>
    </footer>
  </div>
</template>

<style scoped>
.cx-ai-card {
  border-width: 1px;
  border-radius: var(--radius-md, 8px);
  padding: var(--space-4, 16px);
  box-shadow: var(--shadow-xs, 0 1px 2px rgba(8, 18, 13, 0.04));
  margin-bottom: var(--space-4, 16px);
  box-sizing: border-box;
  font-family: var(--font-sans, Inter, sans-serif);
}

.cx-ai-card--proposed {
  border-width: 1.5px;
}

.cx-ai-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3, 12px);
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}

.cx-ai-card__title-group {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}

.cx-ai-card__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--cortex-text, #08120d);
  letter-spacing: -0.005em;
}

.cx-ai-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  font-size: 12px;
  color: var(--cortex-text-muted, #436354);
}

.cx-ai-card__source {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono, "JetBrains Mono", monospace);
}

.cx-ai-card__noop-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: rgba(8, 122, 67, 0.08);
  border: 1px solid var(--cortex-green-600, #087a43);
  border-radius: var(--radius-sm, 6px);
  font-size: 12.5px;
  font-weight: 500;
  color: var(--cortex-green-800, #044727);
  margin-bottom: var(--space-3, 12px);
}

.cx-ai-card__body {
  font-size: 13.5px;
  color: var(--cortex-text-secondary, #264034);
  line-height: 1.45;
}

.cx-ai-card__description {
  margin: 0 0 var(--space-3, 12px) 0;
}

/* Extracted Evidence Box */
.cx-ai-card__evidence-box {
  background-color: var(--cortex-violet-50, #f5f3ff);
  border: 1px solid var(--cortex-violet-200, #ddd6fe);
  border-radius: var(--radius-sm, 6px);
  padding: 10px 12px;
  margin-top: var(--space-3, 12px);
}

.cx-ai-card__evidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.cx-ai-card__evidence-doc {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--cortex-violet-900, #4c1d95);
}

.cx-ai-card__proof-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--cortex-violet-800, #5b21b6);
  background-color: #ffffff;
  border: 1px solid var(--cortex-violet-600, #7c3aed);
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--motion-fast, 120ms ease);
}

.cx-ai-card__proof-btn:hover {
  background-color: var(--cortex-violet-100, #ede9fe);
}

.cx-ai-card__evidence-quote {
  margin: 6px 0;
  padding-left: 10px;
  border-left: 2px solid var(--cortex-violet-600, #7c3aed);
  font-style: italic;
  font-size: 12.5px;
  color: var(--cortex-violet-900, #4c1d95);
}

.cx-ai-card__hash {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 10.5px;
  color: var(--cortex-text-muted, #436354);
  margin-top: 4px;
}

/* Needs Confirmation Box */
.cx-ai-card__confirmation-box {
  background-color: var(--cortex-warning-50, #fffbeb);
  border: 1px solid var(--cortex-warning-500, #f59e0b);
  border-radius: var(--radius-sm, 6px);
  padding: 10px 12px;
  margin-top: var(--space-3, 12px);
}

.cx-ai-card__reason {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--cortex-amber-900, #78350f);
  margin-bottom: 6px;
}

.cx-ai-card__missing-fields {
  margin-top: 6px;
}

.cx-ai-card__missing-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--cortex-amber-900, #78350f);
}

.cx-ai-card__missing-list {
  margin: 4px 0 0 0;
  padding-left: 20px;
  font-family: var(--font-mono, "JetBrains Mono", monospace);
  font-size: 12px;
  color: var(--cortex-amber-800, #92400e);
}

/* Approval Required Box */
.cx-ai-card__approval-box {
  background-color: var(--cortex-warning-50, #fffbeb);
  border: 1.5px solid var(--cortex-amber-700, #b45309);
  border-radius: var(--radius-sm, 6px);
  padding: 12px;
  margin-top: var(--space-3, 12px);
}

.cx-ai-card__approval-notice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--cortex-amber-900, #78350f);
}

.cx-ai-card__approval-notice p {
  margin: 4px 0 0 0;
  font-size: 12.5px;
}

/* Approved / Executed Audit Box */
.cx-ai-card__audit-box {
  background-color: var(--cortex-green-50, #edfbf2);
  border: 1px solid var(--cortex-green-600, #087a43);
  border-radius: var(--radius-sm, 6px);
  padding: 10px 12px;
  margin-top: var(--space-3, 12px);
}

.cx-ai-card__audit-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3, 12px);
  font-size: 12.5px;
  color: var(--cortex-green-800, #044727);
  margin-bottom: 6px;
}

.cx-ai-card__audit-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cx-ai-card__audit-id {
  font-family: var(--font-mono, "JetBrains Mono", monospace);
}

.cx-ai-card__audit-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--cortex-green-800, #044727);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
}

/* Policy Block Box */
.cx-ai-card__policy-box {
  background-color: var(--cortex-danger-50, #fef2f2);
  border: 1.5px solid var(--cortex-red-600, #dc2626);
  border-radius: var(--radius-sm, 6px);
  padding: 12px;
  margin-top: var(--space-3, 12px);
}

.cx-ai-card__policy-rule {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--cortex-red-900, #7f1d1d);
}

.cx-ai-card__policy-code {
  font-size: 13.5px;
}

.cx-ai-card__policy-desc {
  margin: 4px 0 0 0;
  font-size: 12.5px;
  color: var(--cortex-red-800, #991b1b);
}

.cx-ai-card__policy-remediation {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--cortex-red-200, #fecaca);
}

.cx-ai-card__next-label {
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--cortex-red-900, #7f1d1d);
}

.cx-ai-card__next-text {
  margin: 2px 0 0 0;
  font-size: 12.5px;
  color: var(--cortex-text, #08120d);
  font-weight: 500;
}

/* Card Footer & Action Buttons */
.cx-ai-card__footer {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-top: var(--space-4, 16px);
  padding-top: var(--space-3, 12px);
  border-top: 1px solid var(--cortex-border, #cbdcd2);
  flex-wrap: wrap;
}

.cx-ai-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  font-family: var(--font-sans, Inter, sans-serif);
  font-size: 12.5px;
  font-weight: 600;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all var(--motion-fast, 120ms ease);
  box-sizing: border-box;
}

.cx-ai-btn--primary {
  background-color: var(--cortex-green-600, #087a43);
  color: #ffffff;
  border: 1px solid var(--cortex-green-700, #065f34);
}

.cx-ai-btn--primary:hover {
  background-color: var(--cortex-green-700, #065f34);
}

.cx-ai-btn--secondary {
  background-color: #ffffff;
  color: var(--cortex-text, #08120d);
  border: 1px solid var(--cortex-border, #cbdcd2);
}

.cx-ai-btn--secondary:hover {
  background-color: var(--cortex-surface-hover, #e3ece6);
}

.cx-ai-btn--warning {
  background-color: var(--cortex-warning-100, #fef3c7);
  color: var(--cortex-amber-900, #78350f);
  border: 1px solid var(--cortex-amber-700, #b45309);
}

.cx-ai-btn--warning:hover {
  background-color: var(--cortex-warning-50, #fffbeb);
}

.cx-ai-btn--danger-ghost {
  background: transparent;
  color: var(--cortex-danger-700, #b91c1c);
  border: 1px solid transparent;
}

.cx-ai-btn--danger-ghost:hover {
  background-color: var(--cortex-danger-50, #fef2f2);
  border-color: var(--cortex-danger-200, #fecaca);
}
</style>
