<template>
  <div class="dash-page">
    <!-- ── Top bar : retour + déconnexion ── -->
    <header class="dash-topbar">
      <router-link to="/" class="dash-back" :title="$t('nav.homeTitle')">
        <span class="dash-back-arrow material-symbols-outlined" aria-hidden="true">arrow_back</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
      <button
        type="button"
        class="dash-logout"
        @click="onLogout"
        :title="$t('nav.logout')"
      >
        <span class="material-symbols-outlined" aria-hidden="true">logout</span>
        <span>{{ $t('nav.logout') }}</span>
      </button>
    </header>

    <main class="dash-main">
      <!-- ── Hero : org + rôle ── -->
      <section class="dash-hero">
        <div class="dash-hero-eyebrow">{{ $t('client.dashboard.eyebrow') }}</div>
        <h1 class="dash-hero-title">
          {{ heroTitle }}
        </h1>
        <p v-if="orgName" class="dash-hero-subtitle">
          <span class="dash-hero-org">{{ orgName }}</span>
          <span v-if="roleLabel" class="dash-hero-sep" aria-hidden="true">·</span>
          <span v-if="roleLabel" class="dash-hero-role">{{ roleLabel }}</span>
        </p>
        <p v-else class="dash-hero-subtitle">
          {{ $t('client.dashboard.noOrgYet') }}
        </p>
      </section>

      <!-- ── Banner : pas encore d'org ── -->
      <div v-if="orgs.length === 0 && !loading" class="dash-banner" role="status">
        <div class="dash-banner-icon">
          <span class="material-symbols-outlined" aria-hidden="true">schedule</span>
        </div>
        <div class="dash-banner-body">
          <h2 class="dash-banner-title">{{ $t('client.dashboard.pendingTitle') }}</h2>
          <p class="dash-banner-text">{{ $t('client.dashboard.pendingBody') }}</p>
        </div>
      </div>

      <!-- ── Stats (cards) ── -->
      <section v-if="orgs.length > 0" class="dash-stats" :aria-label="$t('client.dashboard.statsAriaLabel')">
        <article class="dash-stat-card">
          <span class="dash-stat-label">{{ $t('client.dashboard.stats.total') }}</span>
          <span class="dash-stat-value">{{ stats.total }}</span>
        </article>
        <article class="dash-stat-card">
          <span class="dash-stat-label">{{ $t('client.dashboard.stats.published') }}</span>
          <span class="dash-stat-value">{{ stats.published }}</span>
        </article>
        <article class="dash-stat-card">
          <span class="dash-stat-label">{{ $t('client.dashboard.stats.brierAvg') }}</span>
          <span class="dash-stat-value">{{ formatBrier(stats.brierAvg) }}</span>
        </article>
      </section>

      <!-- ── Toolbar : commande nouvelle analyse + (US-098) self-service ── -->
      <div v-if="orgs.length > 0" class="dash-toolbar">
        <h2 class="dash-section-title">{{ $t('client.dashboard.simulationsTitle') }}</h2>
        <div class="dash-toolbar-actions">
          <!-- US-098/US-107 — Bouton self-service visible uniquement si l'org a le flag.
               Désormais conduit vers /console (route privative dédiée). -->
          <router-link
            v-if="canSelfService"
            to="/console"
            class="dash-cta dash-cta--secondary"
            :title="$t('dashboard.selfServiceCta.title')"
          >
            <span class="material-symbols-outlined" aria-hidden="true">rocket_launch</span>
            <span>{{ $t('dashboard.selfServiceCta.label') }}</span>
          </router-link>
          <router-link
            :to="{ name: 'Quote', query: { org: 'true' } }"
            class="dash-cta"
            :title="$t('client.dashboard.orderTitle')"
          >
            <span class="material-symbols-outlined" aria-hidden="true">add</span>
            <span>{{ $t('client.dashboard.orderCta') }}</span>
          </router-link>
        </div>
      </div>

      <!-- ── État de chargement ── -->
      <p v-if="loading" class="dash-loading">{{ $t('common.loading') }}</p>

      <!-- ── Erreur globale ── -->
      <p v-if="errorMessage" class="dash-error" role="alert">
        <span class="material-symbols-outlined" aria-hidden="true">error</span>
        <span>{{ errorMessage }}</span>
      </p>

      <!-- ── Table des simulations ── -->
      <section
        v-if="orgs.length > 0 && !loading && simulations.length > 0"
        class="dash-table-wrapper"
      >
        <table class="dash-table">
          <thead>
            <tr>
              <th scope="col">{{ $t('client.dashboard.table.id') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.package') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.created') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.status') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.published') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.outcome') }}</th>
              <th scope="col">{{ $t('client.dashboard.table.brier') }}</th>
              <th scope="col" class="dash-table-actions-col">{{ $t('client.dashboard.table.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sim in simulations" :key="sim.simulation_id">
              <td class="dash-table-id">
                <code>{{ truncateId(sim.simulation_id) }}</code>
              </td>
              <td>{{ sim.package_id || '—' }}</td>
              <td>{{ formatDate(sim.created_at) }}</td>
              <td>
                <span
                  class="dash-pill"
                  :class="`dash-pill--${sim.status || 'pending'}`"
                >
                  {{ statusLabel(sim.status) }}
                </span>
              </td>
              <td>
                <span
                  class="dash-pill"
                  :class="sim.is_published ? 'dash-pill--published' : 'dash-pill--private'"
                >
                  {{ sim.is_published ? $t('client.dashboard.publishedYes') : $t('client.dashboard.publishedNo') }}
                </span>
              </td>
              <td>{{ outcomeLabel(sim.outcome) }}</td>
              <td>{{ sim.brier_score != null ? formatBrier(sim.brier_score) : '—' }}</td>
              <td class="dash-table-actions">
                <router-link
                  :to="{ name: 'Report', params: { reportId: sim.simulation_id } }"
                  class="dash-action-link"
                  :title="$t('client.dashboard.actions.viewTitle')"
                >
                  {{ $t('client.dashboard.actions.view') }}
                </router-link>
                <button
                  v-if="canWrite"
                  type="button"
                  class="dash-action-btn"
                  @click="openOutcomeModal(sim)"
                  :title="$t('client.dashboard.actions.outcomeTitle')"
                >
                  {{ $t('client.dashboard.actions.outcome') }}
                </button>
                <button
                  v-if="canWrite"
                  type="button"
                  class="dash-action-btn"
                  @click="togglePublish(sim)"
                  :disabled="publishingId === sim.simulation_id"
                  :title="$t('client.dashboard.actions.publishTitle')"
                >
                  {{ sim.is_published
                    ? $t('client.dashboard.actions.unpublish')
                    : $t('client.dashboard.actions.publish') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ── Vide ── -->
      <p
        v-else-if="orgs.length > 0 && !loading"
        class="dash-empty"
      >
        {{ $t('client.dashboard.empty') }}
      </p>
    </main>

    <!-- ── Modal : marquer outcome ── -->
    <Teleport to="body">
      <div
        v-if="outcomeModalOpen"
        class="dash-modal-overlay"
        @click.self="closeOutcomeModal"
      >
        <div class="dash-modal" role="dialog" :aria-label="$t('client.dashboard.outcomeModal.title')">
          <header class="dash-modal-header">
            <h3 class="dash-modal-title">{{ $t('client.dashboard.outcomeModal.title') }}</h3>
            <button
              type="button"
              class="dash-modal-close"
              @click="closeOutcomeModal"
              :aria-label="$t('common.close')"
            >
              <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
          </header>
          <form class="dash-modal-form" @submit.prevent="submitOutcome">
            <label class="dash-field">
              <span class="dash-field-label">{{ $t('client.dashboard.outcomeModal.labelField') }}</span>
              <select v-model="outcomeForm.label" class="dash-input">
                <option value="called_it">{{ $t('client.dashboard.outcomeLabels.called_it') }}</option>
                <option value="partial">{{ $t('client.dashboard.outcomeLabels.partial') }}</option>
                <option value="wrong">{{ $t('client.dashboard.outcomeLabels.wrong') }}</option>
              </select>
            </label>
            <label class="dash-field">
              <span class="dash-field-label">{{ $t('client.dashboard.outcomeModal.observedAt') }}</span>
              <input
                v-model="outcomeForm.observed_at"
                type="date"
                class="dash-input"
                :aria-label="$t('client.dashboard.outcomeModal.observedAt')"
              />
            </label>
            <label class="dash-field">
              <span class="dash-field-label">{{ $t('client.dashboard.outcomeModal.sourceUrl') }}</span>
              <input
                v-model.trim="outcomeForm.source_url"
                type="url"
                class="dash-input"
                placeholder="https://"
                :aria-label="$t('client.dashboard.outcomeModal.sourceUrl')"
              />
            </label>
            <label class="dash-field">
              <span class="dash-field-label">{{ $t('client.dashboard.outcomeModal.notes') }}</span>
              <textarea
                v-model.trim="outcomeForm.notes"
                class="dash-input dash-modal-textarea"
                rows="3"
                :aria-label="$t('client.dashboard.outcomeModal.notes')"
              ></textarea>
            </label>
            <p v-if="outcomeError" class="dash-error" role="alert">
              <span class="material-symbols-outlined" aria-hidden="true">error</span>
              <span>{{ outcomeError }}</span>
            </p>
            <div class="dash-modal-actions">
              <button
                type="button"
                class="dash-action-btn"
                @click="closeOutcomeModal"
                :disabled="outcomeSubmitting"
              >
                {{ $t('common.cancel') }}
              </button>
              <button
                type="submit"
                class="dash-cta"
                :disabled="outcomeSubmitting || !outcomeForm.label"
              >
                {{ outcomeSubmitting
                  ? $t('client.dashboard.outcomeModal.submitting')
                  : $t('client.dashboard.outcomeModal.submit') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  listClientSimulations,
  markOutcome,
  publishSimulation
} from '../api/client'

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')
const simulations = ref([])
const publishingId = ref('')

// ── Modal outcome ─────────────────────────────────────────────────
const outcomeModalOpen = ref(false)
const outcomeSubmitting = ref(false)
const outcomeError = ref('')
const outcomeTargetId = ref('')
const outcomeForm = reactive({
  label: 'called_it',
  observed_at: '',
  source_url: '',
  notes: ''
})

// ── Computed ──────────────────────────────────────────────────────
const orgs = computed(() => auth.orgs)
const orgName = computed(() => auth.currentOrg?.name || '')
const roleLabel = computed(() => {
  const role = auth.currentRole
  if (!role) return ''
  return t(`client.dashboard.roles.${role}`)
})
const heroTitle = computed(() => {
  if (!auth.user) return t('client.dashboard.heroFallback')
  return t('client.dashboard.heroTitle')
})
const canWrite = computed(() => auth.canWrite)
// US-098 / US-099 — bouton self-service visible si :
//   - super-admin Bassira (toujours autorisé), OU
//   - membre actif d'une org dont self_service_enabled = true
const canSelfService = computed(() => {
  if (auth.isSuperAdmin) return true
  return Boolean(auth.currentOrg?.self_service_enabled)
})

const stats = computed(() => {
  const total = simulations.value.length
  const published = simulations.value.filter((s) => s.is_published).length
  const briers = simulations.value
    .map((s) => s.brier_score)
    .filter((b) => typeof b === 'number' && !Number.isNaN(b))
  const brierAvg = briers.length > 0
    ? briers.reduce((acc, b) => acc + b, 0) / briers.length
    : null
  return { total, published, brierAvg }
})

// ── Methods ───────────────────────────────────────────────────────
function truncateId(id) {
  if (!id) return ''
  return id.length > 16 ? `${id.slice(0, 16)}…` : id
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleDateString(locale.value || 'fr', {
      year: 'numeric',
      month: 'short',
      day: '2-digit'
    })
  } catch (_) {
    return iso
  }
}

function formatBrier(value) {
  if (value == null || Number.isNaN(value)) return '—'
  return Number(value).toFixed(3)
}

function statusLabel(status) {
  const key = status || 'pending'
  const k = `client.dashboard.statusLabels.${key}`
  const v = t(k)
  return v && v !== k ? v : key
}

function outcomeLabel(outcome) {
  if (!outcome || !outcome.label) return '—'
  const k = `client.dashboard.outcomeLabels.${outcome.label}`
  const v = t(k)
  return v && v !== k ? v : outcome.label
}

async function fetchSimulations() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await listClientSimulations()
    // Tolère les 2 formats : { data: { simulations: [...] } } ou direct.
    const payload = res?.data || res
    simulations.value = Array.isArray(payload?.simulations)
      ? payload.simulations
      : Array.isArray(payload)
        ? payload
        : []
  } catch (err) {
    if (err?.response?.status === 401) {
      // Token invalide → redirection login.
      await auth.logout()
      router.push({ name: 'Login', query: { redirect: '/client/dashboard' } })
      return
    }
    errorMessage.value = err?.response?.data?.error
      || err?.message
      || t('client.dashboard.errors.fetchFailed')
    simulations.value = []
  } finally {
    loading.value = false
  }
}

async function togglePublish(sim) {
  if (!canWrite.value) return
  publishingId.value = sim.simulation_id
  try {
    await publishSimulation(sim.simulation_id, {
      is_published: !sim.is_published
    })
    sim.is_published = !sim.is_published
  } catch (err) {
    errorMessage.value = err?.response?.data?.error
      || err?.message
      || t('client.dashboard.errors.publishFailed')
  } finally {
    publishingId.value = ''
  }
}

function openOutcomeModal(sim) {
  outcomeTargetId.value = sim.simulation_id
  outcomeForm.label = sim.outcome?.label || 'called_it'
  outcomeForm.observed_at = sim.outcome?.observed_at?.slice(0, 10) || ''
  outcomeForm.source_url = sim.outcome?.source_url || ''
  outcomeForm.notes = sim.outcome?.notes || ''
  outcomeError.value = ''
  outcomeModalOpen.value = true
}

function closeOutcomeModal() {
  outcomeModalOpen.value = false
  outcomeTargetId.value = ''
  outcomeError.value = ''
}

async function submitOutcome() {
  if (!outcomeTargetId.value || outcomeSubmitting.value) return
  outcomeSubmitting.value = true
  outcomeError.value = ''
  try {
    const payload = {
      label: outcomeForm.label,
      observed_at: outcomeForm.observed_at || null,
      source_url: outcomeForm.source_url || null,
      notes: outcomeForm.notes || null
    }
    const res = await markOutcome(outcomeTargetId.value, payload)
    // Met à jour la sim localement.
    const updated = res?.data?.simulation || res?.simulation || null
    const target = simulations.value.find((s) => s.simulation_id === outcomeTargetId.value)
    if (target) {
      target.outcome = updated?.outcome || payload
      if (updated?.brier_score != null) target.brier_score = updated.brier_score
    }
    closeOutcomeModal()
  } catch (err) {
    outcomeError.value = err?.response?.data?.error
      || err?.message
      || t('client.dashboard.errors.outcomeFailed')
  } finally {
    outcomeSubmitting.value = false
  }
}

async function onLogout() {
  await auth.logout()
  router.push('/')
}

onMounted(async () => {
  // Charge le profil si pas encore fait (cas où le user vient juste
  // de se connecter et la session était déjà persistée).
  if (!auth.profileLoaded && auth.isAuthenticated) {
    try {
      await auth.fetchProfile()
    } catch (err) {
      errorMessage.value = err?.message || t('client.dashboard.errors.profileFailed')
    }
  }
  if (auth.orgs.length > 0) {
    await fetchSimulations()
  }
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   CLIENT DASHBOARD — palette --wi-* exclusive, RTL-safe
   ═══════════════════════════════════════════════════════════ */

.dash-page {
  min-height: 100vh;
  background: var(--wi-bg);
  color: var(--wi-on-surface);
  font-family: var(--wi-font-body);
  font-size: 16px;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
}

.dash-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-block: var(--wi-space-md);
  padding-inline: var(--wi-space-lg);
  border-block-end: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
}

.dash-back,
.dash-logout {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  color: var(--wi-on-surface-variant);
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 8px 14px;
  border-radius: var(--wi-radius-pill);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition: background 160ms ease, color 160ms ease, border-color 160ms ease;
}

.dash-back:hover,
.dash-logout:hover {
  background: var(--wi-surface-container-low);
  color: var(--wi-primary);
}

.dash-back-arrow {
  font-size: 18px;
}

[dir='rtl'] .dash-back-arrow {
  transform: scaleX(-1);
}

.dash-main {
  flex: 1;
  width: 100%;
  max-width: 1240px;
  margin-inline: auto;
  padding: var(--wi-space-lg) var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}

/* ── Hero ─────────────────────────────────────────────── */
.dash-hero {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
  box-shadow: var(--wi-shadow-sm);
}

.dash-hero-eyebrow {
  display: inline-block;
  font-family: var(--wi-font-heading);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-primary);
  background: var(--wi-primary-container-soft);
  border: 1px solid var(--wi-primary-container-edge);
  border-radius: var(--wi-radius-pill);
  padding: 6px 14px;
  margin-block-end: var(--wi-space-sm);
}

.dash-hero-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  margin-block-end: 8px;
}

.dash-hero-subtitle {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.dash-hero-org {
  font-weight: 600;
  color: var(--wi-on-surface);
}

.dash-hero-sep {
  color: var(--wi-outline);
}

.dash-hero-role {
  color: var(--wi-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 13px;
}

/* ── Banner ───────────────────────────────────────────── */
.dash-banner {
  display: flex;
  align-items: flex-start;
  gap: var(--wi-space-sm);
  background: var(--wi-surface-container);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
}

.dash-banner-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--wi-primary-container-soft);
  color: var(--wi-primary);
  flex-shrink: 0;
}

.dash-banner-icon .material-symbols-outlined {
  font-size: 24px;
}

.dash-banner-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  margin-block-end: 6px;
  color: var(--wi-on-surface);
}

.dash-banner-text {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-body-md);
  line-height: 1.6;
}

/* ── Stats grid ──────────────────────────────────────── */
.dash-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--wi-space-sm);
}

.dash-stat-card {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: var(--wi-shadow-sm);
}

.dash-stat-label {
  font-size: var(--wi-label-sm);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: var(--wi-label-sm-tracking);
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}

.dash-stat-value {
  font-family: var(--wi-font-heading);
  font-size: 36px;
  font-weight: 600;
  line-height: 1;
  color: var(--wi-primary);
}

/* ── Toolbar ─────────────────────────────────────────── */
.dash-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--wi-space-sm);
  margin-block-start: var(--wi-space-sm);
}

.dash-section-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0;
}

.dash-cta {
  appearance: none;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-md);
  font-weight: 600;
  letter-spacing: 0.02em;
  border-radius: var(--wi-radius-pill);
  padding: 12px 22px;
  cursor: pointer;
  text-decoration: none;
  transition: background 160ms ease, box-shadow 160ms ease;
}

.dash-cta:hover:not(:disabled) {
  background: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-md);
}

.dash-cta:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* US-098 — Toolbar avec deux actions (self-service + commande) */
.dash-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wi-space-sm, 8px);
}
.dash-cta--secondary {
  background: var(--wi-surface-container-low, var(--wi-surface));
  color: var(--wi-primary);
  border: 1px solid var(--wi-primary);
}
.dash-cta--secondary:hover:not(:disabled) {
  background: var(--wi-primary-soft, var(--wi-surface));
  box-shadow: var(--wi-shadow-sm, none);
}

/* ── Loading / error / empty ─────────────────────────── */
.dash-loading,
.dash-empty {
  text-align: center;
  color: var(--wi-on-surface-variant);
  padding: var(--wi-space-md);
}

.dash-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-radius: var(--wi-radius-md);
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.4;
}

/* ── Table ───────────────────────────────────────────── */
.dash-table-wrapper {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  overflow-x: auto;
  box-shadow: var(--wi-shadow-sm);
}

.dash-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.dash-table th,
.dash-table td {
  padding: 12px 16px;
  text-align: start;
  vertical-align: middle;
  border-block-end: 1px solid var(--wi-outline-variant);
}

.dash-table th {
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface-variant);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 12px;
  white-space: nowrap;
}

.dash-table tbody tr:last-child td {
  border-block-end: none;
}

.dash-table tbody tr:hover {
  background: var(--wi-surface-container-low);
}

.dash-table-id code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  background: var(--wi-surface-container);
  padding: 3px 6px;
  border-radius: var(--wi-radius-sm);
}

.dash-table-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.dash-table-actions-col {
  width: 240px;
}

.dash-action-link,
.dash-action-btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill);
  text-decoration: none;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
}

.dash-action-link:hover,
.dash-action-btn:hover:not(:disabled) {
  background: var(--wi-primary-container-soft);
  border-color: var(--wi-primary);
  color: var(--wi-primary);
}

.dash-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Pills (status / published) ──────────────────────── */
.dash-pill {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  background: var(--wi-surface-container);
  color: var(--wi-on-surface-variant);
  border: 1px solid var(--wi-outline-variant);
}

.dash-pill--running,
.dash-pill--in_progress {
  background: var(--wi-tertiary-container);
  color: var(--wi-on-tertiary-container);
  border-color: var(--wi-tertiary);
}

.dash-pill--completed,
.dash-pill--published {
  background: var(--wi-secondary-container);
  color: var(--wi-on-secondary-container);
  border-color: var(--wi-secondary);
}

.dash-pill--failed,
.dash-pill--error {
  background: var(--wi-error-container);
  color: var(--wi-on-error-container);
  border-color: var(--wi-error);
}

.dash-pill--pending,
.dash-pill--private {
  background: var(--wi-surface-container);
  color: var(--wi-on-surface-variant);
}

/* ── Modal outcome ──────────────────────────────────── */
.dash-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(36, 25, 21, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--wi-space-md);
  z-index: 1400;
}

.dash-modal {
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  box-shadow: var(--wi-shadow-lg);
  max-width: 520px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.dash-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-md);
  border-block-end: 1px solid var(--wi-outline-variant);
}

.dash-modal-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0;
}

.dash-modal-close {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--wi-on-surface-variant);
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 160ms ease, color 160ms ease;
}

.dash-modal-close:hover {
  background: var(--wi-surface-container-low);
  color: var(--wi-primary);
}

.dash-modal-form {
  padding: var(--wi-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-sm);
}

.dash-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dash-field-label {
  font-size: var(--wi-label-sm);
  font-weight: var(--wi-label-sm-weight);
  letter-spacing: var(--wi-label-sm-tracking);
  color: var(--wi-on-surface-variant);
}

.dash-input {
  appearance: none;
  width: 100%;
  background: var(--wi-surface-container-low);
  color: var(--wi-on-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: 12px 14px;
  font-family: inherit;
  font-size: var(--wi-body-md);
  line-height: 1.4;
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}

.dash-input:focus {
  outline: none;
  border-color: var(--wi-primary);
  background: var(--wi-surface);
  box-shadow: 0 0 0 3px var(--wi-primary-container-soft);
}

.dash-modal-textarea {
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
}

.dash-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--wi-space-xs);
  margin-block-start: var(--wi-space-xs);
}

@media (max-width: 720px) {
  .dash-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .dash-table-actions-col {
    width: auto;
  }
}
</style>
