<template>
  <!--
    ReportProgressTimeline (US-110) — 4-step horizontal timeline
    Stages : graph_build → simulation → agents → report.
    Tokens : --wi-* exclusively. RTL-friendly (block-direction follows
    document dir). i18n FR/EN/AR via $t('report.progress.*').

    Polling is delegated to the parent (ReportView) so we don't duplicate
    HTTP calls; we receive `stages` already computed from getReport +
    getSimulation responses.
  -->
  <section class="rpt-progress" :aria-label="$t('report.progress.title')">
    <header class="rpt-progress-head">
      <span class="rpt-progress-title">{{ $t('report.progress.title') }}</span>
      <span class="rpt-progress-counter mono">
        {{ doneCount }} / {{ stages.length }}
      </span>
    </header>

    <ol class="rpt-progress-track">
      <li
        v-for="(stage, idx) in stages"
        :key="stage.id"
        class="rpt-progress-step"
        :class="`is-${stage.status}`"
        :aria-current="stage.status === 'in_progress' ? 'step' : null"
      >
        <div class="rpt-progress-marker">
          <span class="rpt-progress-index mono">{{ idx + 1 }}</span>
          <!-- Done: check svg / In progress: spinner / Error: cross -->
          <svg
            v-if="stage.status === 'done'"
            class="rpt-progress-icon"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span
            v-else-if="stage.status === 'in_progress'"
            class="rpt-progress-spin"
            aria-hidden="true"
          ></span>
          <svg
            v-else-if="stage.status === 'error'"
            class="rpt-progress-icon"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
            aria-hidden="true"
          >
            <line x1="6" y1="6" x2="18" y2="18"></line>
            <line x1="6" y1="18" x2="18" y2="6"></line>
          </svg>
        </div>
        <div class="rpt-progress-body">
          <span class="rpt-progress-step-title">
            {{ $t(`report.progress.stages.${stage.id}.title`) }}
          </span>
          <span class="rpt-progress-step-sub">
            {{ $t(`report.progress.stages.${stage.id}.subtitle`) }}
          </span>
          <span class="rpt-progress-step-status" :class="`status-${stage.status}`">
            {{ statusLabel(stage.status) }}
          </span>
        </div>
        <div
          v-if="idx < stages.length - 1"
          class="rpt-progress-link"
          :class="{ 'is-done': stage.status === 'done' }"
          aria-hidden="true"
        ></div>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  // stages: array of { id, status } where:
  // - id ∈ { 'graphBuild', 'simulation', 'agents', 'report' }
  // - status ∈ { 'pending', 'in_progress', 'done', 'error' }
  stages: {
    type: Array,
    required: true,
    validator: (val) =>
      Array.isArray(val) &&
      val.every(
        (s) =>
          s &&
          typeof s.id === 'string' &&
          ['pending', 'in_progress', 'done', 'error'].includes(s.status)
      )
  }
})

const { t } = useI18n()

const doneCount = computed(() => props.stages.filter((s) => s.status === 'done').length)

const statusLabel = (status) => {
  const map = {
    pending: 'pending',
    in_progress: 'inProgress',
    done: 'done',
    error: 'error'
  }
  return t(`report.progress.status.${map[status] || 'pending'}`)
}
</script>

<style scoped>
.rpt-progress {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md) var(--wi-space-lg);
  box-shadow: var(--wi-shadow-sm);
}

.rpt-progress-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--wi-space-md);
  gap: var(--wi-space-sm);
}

.rpt-progress-title {
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--wi-on-primary-container);
}

.rpt-progress-counter {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
}

.rpt-progress-track {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  position: relative;
}

.rpt-progress-step {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--wi-space-xs);
  padding-inline-end: var(--wi-space-md);
  min-width: 0;
}

.rpt-progress-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--wi-bg);
  border: 2px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 700;
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  transition: background var(--ms-transition), border-color var(--ms-transition), color var(--ms-transition);
}

.rpt-progress-step.is-done .rpt-progress-marker {
  background: var(--wi-secondary-container);
  border-color: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
}

.rpt-progress-step.is-in_progress .rpt-progress-marker {
  background: var(--wi-primary-container);
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
}

.rpt-progress-step.is-error .rpt-progress-marker {
  background: var(--wi-error);
  border-color: var(--wi-error);
  color: var(--wi-bg);
}

.rpt-progress-step.is-done .rpt-progress-index,
.rpt-progress-step.is-in_progress .rpt-progress-index,
.rpt-progress-step.is-error .rpt-progress-index {
  /* Hide the index when an icon takes its place */
  display: none;
}

.rpt-progress-icon {
  flex-shrink: 0;
}

.rpt-progress-spin {
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: rpt-progress-spin 0.9s linear infinite;
}

@keyframes rpt-progress-spin {
  to {
    transform: rotate(360deg);
  }
}

.rpt-progress-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.rpt-progress-step-title {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-surface);
  line-height: 1.3;
}

.rpt-progress-step-sub {
  font-family: var(--wi-font-body);
  font-size: 12px;
  font-weight: 400;
  color: var(--wi-on-surface-variant);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rpt-progress-step-status {
  font-family: var(--ms-font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin-top: 2px;
}

.rpt-progress-step-status.status-done {
  color: var(--wi-on-secondary-container);
}
.rpt-progress-step-status.status-in_progress {
  color: var(--wi-on-primary-container);
}
.rpt-progress-step-status.status-pending {
  color: var(--wi-outline);
}
.rpt-progress-step-status.status-error {
  color: var(--wi-error);
}

.rpt-progress-link {
  position: absolute;
  top: 13px;
  /* Use logical insets so the line flips correctly in RTL. */
  inset-inline-start: 28px;
  inset-inline-end: 0;
  height: 2px;
  background: var(--wi-outline-variant);
  z-index: 0;
  transition: background var(--ms-transition);
}

.rpt-progress-link.is-done {
  background: var(--wi-secondary-container);
}

@media (max-width: 768px) {
  .rpt-progress-track {
    grid-template-columns: 1fr;
    gap: var(--wi-space-sm);
  }
  .rpt-progress-step {
    flex-direction: row;
    align-items: flex-start;
    gap: var(--wi-space-sm);
    padding-inline-end: 0;
  }
  .rpt-progress-link {
    /* Vertical link in mobile/stacked layout */
    top: 28px;
    bottom: -8px;
    inset-inline-start: 13px;
    inset-inline-end: auto;
    width: 2px;
    height: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rpt-progress-spin {
    animation: none;
  }
  .rpt-progress-marker {
    transition: none;
  }
}
</style>
