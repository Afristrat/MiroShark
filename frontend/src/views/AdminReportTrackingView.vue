<template>
  <div class="art-page">
    <!-- Topbar -->
    <header class="art-topbar">
      <router-link to="/" class="art-back" :title="$t('nav.homeTitle') || 'Accueil'">
        <span class="art-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') || 'BASSIRA' }}</span>
      </router-link>
      <div class="art-topbar-right">
        <router-link to="/admin/quotes" class="art-pill art-pill--ghost">
          {{ $t('adminQuotes.title') || 'Devis' }}
        </router-link>
        <router-link to="/client/dashboard" class="art-pill art-pill--ghost">
          {{ $t('nav.dashboard') || 'Mon espace' }}
        </router-link>
      </div>
    </header>

    <main class="art-main">
      <!-- Hero -->
      <section class="art-hero">
        <h1 class="art-headline">
          {{ $t('adminReportTracking.title') || 'Suivi des livraisons' }}
        </h1>
        <p class="art-sub">
          {{ $t('adminReportTracking.subtitle') || 'Historique des livraisons et téléchargements de ce rapport.' }}
        </p>
        <p class="art-report-id">
          <code>{{ reportId }}</code>
        </p>
      </section>

      <!-- Actions -->
      <section class="art-actions">
        <button
          type="button"
          class="art-btn art-btn--primary"
          @click="openDeliverModal"
          :disabled="loadingDeliveries"
        >
          + {{ $t('adminReportTracking.deliverBtn') || 'Livrer à un destinataire' }}
        </button>
        <button
          type="button"
          class="art-btn art-btn--secondary"
          @click="loadDeliveries"
          :disabled="loadingDeliveries"
        >
          ↻ {{ loadingDeliveries ? ($t('adminReportTracking.loading') || 'Chargement…') : 'Rafraîchir' }}
        </button>
      </section>

      <!-- État chargement / erreur -->
      <p v-if="loadingDeliveries" class="art-state">
        {{ $t('adminReportTracking.loading') || 'Chargement des livraisons…' }}
      </p>
      <p v-else-if="loadError" class="art-state art-state--error" role="alert">
        {{ loadError }}
      </p>
      <p v-else-if="deliveries.length === 0" class="art-state">
        {{ $t('adminReportTracking.empty') || 'Aucune livraison pour ce rapport.' }}
      </p>

      <!-- Table des livraisons -->
      <section v-if="deliveries.length > 0" class="art-table-card">
        <table class="art-table" role="grid">
          <thead>
            <tr>
              <th>{{ $t('adminReportTracking.table.recipient') || 'Destinataire' }}</th>
              <th>{{ $t('adminReportTracking.table.language') || 'Langue' }}</th>
              <th>{{ $t('adminReportTracking.table.status') || 'Statut' }}</th>
              <th>{{ $t('adminReportTracking.table.sent') || 'Envoyé le' }}</th>
              <th>{{ $t('adminReportTracking.table.expires') || 'Expire le' }}</th>
              <th>{{ $t('adminReportTracking.table.downloads') || 'Téléchargements' }}</th>
              <th>{{ $t('adminReportTracking.table.actions') || 'Actions' }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="delivery in deliveries" :key="delivery.id">
              <!-- Ligne principale de la livraison -->
              <tr
                class="art-row"
                :class="{ 'art-row--expanded': expandedDelivery === delivery.id }"
              >
                <td class="art-cell-email">
                  <div class="art-email">{{ delivery.recipient_email }}</div>
                  <div class="art-name">{{ delivery.recipient_name || '—' }}</div>
                </td>
                <td>
                  <span class="art-lang-badge">{{ (delivery.language || 'fr').toUpperCase() }}</span>
                </td>
                <td>
                  <span
                    class="art-status-pill"
                    :class="`art-status-pill--${delivery.display_status || delivery.email_status}`"
                  >
                    {{ statusLabel(delivery.display_status || delivery.email_status) }}
                  </span>
                </td>
                <td class="art-cell-date">
                  {{ delivery.sent_at ? formatDate(delivery.sent_at) : '—' }}
                </td>
                <td class="art-cell-date">
                  {{ delivery.expires_at ? formatDate(delivery.expires_at) : '—' }}
                </td>
                <td class="art-cell-count">
                  <button
                    type="button"
                    class="art-count-btn"
                    @click="toggleDownloads(delivery.id)"
                    :aria-expanded="expandedDelivery === delivery.id"
                  >
                    {{ downloadCounts[delivery.id] !== undefined
                        ? downloadCounts[delivery.id]
                        : '…' }}
                    <span class="art-count-arrow" aria-hidden="true">
                      {{ expandedDelivery === delivery.id ? '▲' : '▼' }}
                    </span>
                  </button>
                </td>
                <td class="art-cell-actions">
                  <button
                    type="button"
                    class="art-action art-action--resend"
                    :disabled="resendingId === delivery.id"
                    @click="resendLink(delivery)"
                  >
                    {{ resendingId === delivery.id
                        ? ($t('adminReportTracking.resending') || 'Renvoi…')
                        : ($t('adminReportTracking.resend') || 'Renvoyer le lien') }}
                  </button>
                </td>
              </tr>

              <!-- Ligne étendue : tracking téléchargements -->
              <tr
                v-if="expandedDelivery === delivery.id"
                class="art-row art-row--downloads"
              >
                <td colspan="7">
                  <div class="art-downloads-panel">
                    <h3 class="art-downloads-title">
                      {{ $t('adminReportTracking.downloads.title') || 'Téléchargements' }}
                    </h3>

                    <p v-if="loadingDownloads === delivery.id" class="art-state">
                      {{ $t('adminReportTracking.loading') || 'Chargement…' }}
                    </p>
                    <p
                      v-else-if="!downloads[delivery.id] || downloads[delivery.id].length === 0"
                      class="art-state art-state--muted"
                    >
                      {{ $t('adminReportTracking.downloads.empty') || 'Aucun téléchargement enregistré.' }}
                    </p>
                    <table v-else class="art-downloads-table">
                      <thead>
                        <tr>
                          <th>{{ $t('adminReportTracking.downloads.date') || 'Date' }}</th>
                          <th>{{ $t('adminReportTracking.downloads.country') || 'Pays' }}</th>
                          <th>{{ $t('adminReportTracking.downloads.ip') || 'IP' }}</th>
                          <th>{{ $t('adminReportTracking.downloads.ua') || 'Navigateur' }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr
                          v-for="dl in downloads[delivery.id]"
                          :key="dl.id"
                          class="art-dl-row"
                        >
                          <td>{{ formatDate(dl.downloaded_at) }}</td>
                          <td>
                            <span v-if="dl.country_code" class="art-geo">
                              {{ countryFlag(dl.country_code) }} {{ dl.country_code }}
                            </span>
                            <span v-else>—</span>
                          </td>
                          <td class="art-ip">{{ dl.ip_address || '—' }}</td>
                          <td class="art-ua" :title="dl.user_agent || ''">
                            {{ truncateUa(dl.user_agent) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </section>

      <!-- Feedback messages -->
      <div
        v-if="feedbackMsg"
        class="art-feedback"
        :class="feedbackOk ? 'art-feedback--ok' : 'art-feedback--err'"
        role="status"
        aria-live="polite"
      >
        {{ feedbackMsg }}
      </div>
    </main>

    <!-- Modal : livrer le rapport -->
    <div
      v-if="showDeliverModal"
      class="art-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="$t('adminReportTracking.modal.title') || 'Livrer le rapport'"
      @keydown.esc="closeDeliverModal"
    >
      <div class="art-modal" @click.stop>
        <header class="art-modal-header">
          <h2 class="art-modal-title">
            {{ $t('adminReportTracking.modal.title') || 'Livrer le rapport' }}
          </h2>
          <button type="button" class="art-modal-close" @click="closeDeliverModal" aria-label="Fermer">×</button>
        </header>

        <form class="art-modal-form" @submit.prevent="submitDelivery">
          <!-- Email -->
          <div class="art-field">
            <label for="art-recipient-email">
              {{ $t('adminReportTracking.modal.recipientEmail') || 'Email du destinataire' }}
            </label>
            <input
              id="art-recipient-email"
              v-model.trim="deliverForm.recipientEmail"
              type="email"
              required
              class="art-input"
              placeholder="client@example.com"
              autocomplete="off"
            />
          </div>

          <!-- Nom -->
          <div class="art-field">
            <label for="art-recipient-name">
              {{ $t('adminReportTracking.modal.recipientName') || 'Nom du destinataire' }}
            </label>
            <input
              id="art-recipient-name"
              v-model.trim="deliverForm.recipientName"
              type="text"
              class="art-input"
              placeholder="Jean Dupont"
            />
          </div>

          <!-- Durée de validité -->
          <div class="art-field">
            <label for="art-expiry-days">
              {{ $t('adminReportTracking.modal.expiryDays') || 'Durée de validité (jours)' }}
            </label>
            <input
              id="art-expiry-days"
              v-model.number="deliverForm.expiryDays"
              type="number"
              min="1"
              max="90"
              class="art-input"
            />
          </div>

          <!-- Langue -->
          <div class="art-field">
            <label for="art-lang-select">
              {{ $t('adminReportTracking.modal.language') || 'Langue de l\'email' }}
            </label>
            <div class="art-lang-btns" role="group" id="art-lang-select">
              <button
                v-for="lang in ['fr', 'en', 'ar']"
                :key="lang"
                type="button"
                class="art-lang-btn"
                :class="{ 'art-lang-btn--active': deliverForm.language === lang }"
                @click="deliverForm.language = lang"
              >
                {{ lang.toUpperCase() }}
              </button>
            </div>
          </div>

          <!-- Boutons -->
          <footer class="art-modal-footer">
            <button
              type="button"
              class="art-btn art-btn--ghost"
              @click="closeDeliverModal"
              :disabled="submittingDelivery"
            >
              {{ $t('adminReportTracking.modal.cancel') || 'Annuler' }}
            </button>
            <button
              type="submit"
              class="art-btn art-btn--primary"
              :disabled="submittingDelivery || !deliverForm.recipientEmail"
            >
              {{ submittingDelivery
                  ? ($t('adminReportTracking.modal.sending') || 'Envoi…')
                  : ($t('adminReportTracking.modal.submit') || 'Envoyer le lien') }}
            </button>
          </footer>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const route  = useRoute()
const { t }  = useI18n()
const auth   = useAuthStore()

const reportId = ref<string>(String(route.params.id || ''))

// ─── State ───────────────────────────────────────────────────────────────────

type Delivery = {
  id: string
  report_id: string
  version: number
  recipient_email: string
  recipient_name: string
  language: string
  email_status: string
  display_status: string
  sent_at: string | null
  expires_at: string | null
}

type DownloadRecord = {
  id: string
  delivery_id: string
  downloaded_at: string
  ip_address: string | null
  user_agent: string | null
  country_code: string | null
}

const deliveries         = ref<Delivery[]>([])
const downloads          = ref<Record<string, DownloadRecord[]>>({})
const downloadCounts     = ref<Record<string, number>>({})
const loadingDeliveries  = ref(false)
const loadingDownloads   = ref<string | null>(null)
const loadError          = ref<string | null>(null)
const expandedDelivery   = ref<string | null>(null)
const resendingId        = ref<string | null>(null)
const feedbackMsg        = ref<string | null>(null)
const feedbackOk         = ref(true)

const showDeliverModal    = ref(false)
const submittingDelivery  = ref(false)
const deliverForm = reactive({
  recipientEmail: '',
  recipientName:  '',
  expiryDays:     7,
  language:       'fr',
})

// ─── API helpers ─────────────────────────────────────────────────────────────

function _apiBase(): string {
  return import.meta.env.VITE_API_URL || ''
}

async function _authedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const session = await auth.getSession?.()
  const token   = session?.access_token ?? ''
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })
}

// ─── Data loading ─────────────────────────────────────────────────────────────

async function loadDeliveries(): Promise<void> {
  if (!reportId.value) return
  loadingDeliveries.value = true
  loadError.value = null
  try {
    const res = await _authedFetch(
      `${_apiBase()}/api/admin/reports/${encodeURIComponent(reportId.value)}/deliveries`,
    )
    if (!res.ok) {
      loadError.value = `Erreur ${res.status}`
      return
    }
    const json = await res.json()
    deliveries.value = (json.data?.deliveries ?? []) as Delivery[]
    // Pré-charger les compteurs de téléchargements
    for (const d of deliveries.value) {
      downloadCounts.value[d.id] = 0
    }
  } catch (err) {
    loadError.value = String(err)
  } finally {
    loadingDeliveries.value = false
  }
}

async function loadDownloads(deliveryId: string): Promise<void> {
  loadingDownloads.value = deliveryId
  try {
    const res = await _authedFetch(
      `${_apiBase()}/api/admin/reports/${encodeURIComponent(reportId.value)}/deliveries/${encodeURIComponent(deliveryId)}/downloads`,
    )
    if (!res.ok) return
    const json = await res.json()
    const rows = (json.data?.downloads ?? []) as DownloadRecord[]
    downloads.value  = { ...downloads.value, [deliveryId]: rows }
    downloadCounts.value = { ...downloadCounts.value, [deliveryId]: rows.length }
  } finally {
    loadingDownloads.value = null
  }
}

// ─── UI interactions ──────────────────────────────────────────────────────────

function toggleDownloads(deliveryId: string): void {
  if (expandedDelivery.value === deliveryId) {
    expandedDelivery.value = null
    return
  }
  expandedDelivery.value = deliveryId
  if (!downloads.value[deliveryId]) {
    loadDownloads(deliveryId)
  }
}

async function resendLink(delivery: Delivery): Promise<void> {
  resendingId.value = delivery.id
  feedbackMsg.value = null
  try {
    const res = await _authedFetch(
      `${_apiBase()}/api/admin/reports/${encodeURIComponent(reportId.value)}/deliveries/${encodeURIComponent(delivery.id)}/resend`,
      { method: 'POST', body: JSON.stringify({ expiry_days: 7 }) },
    )
    if (res.ok) {
      feedbackMsg.value = t('adminReportTracking.resendSuccess') || 'Nouveau lien envoyé.'
      feedbackOk.value  = true
      await loadDeliveries()
    } else {
      feedbackMsg.value = t('adminReportTracking.resendFailed') || 'Échec du renvoi.'
      feedbackOk.value  = false
    }
  } catch (err) {
    feedbackMsg.value = String(err)
    feedbackOk.value  = false
  } finally {
    resendingId.value = null
    setTimeout(() => { feedbackMsg.value = null }, 4000)
  }
}

function openDeliverModal(): void {
  deliverForm.recipientEmail = ''
  deliverForm.recipientName  = ''
  deliverForm.expiryDays     = 7
  deliverForm.language       = 'fr'
  showDeliverModal.value     = true
}

function closeDeliverModal(): void {
  showDeliverModal.value = false
}

async function submitDelivery(): Promise<void> {
  if (!deliverForm.recipientEmail) return
  submittingDelivery.value = true
  feedbackMsg.value = null
  try {
    const res = await _authedFetch(
      `${_apiBase()}/api/admin/reports/${encodeURIComponent(reportId.value)}/deliver`,
      {
        method: 'POST',
        body: JSON.stringify({
          recipient_email: deliverForm.recipientEmail,
          recipient_name:  deliverForm.recipientName,
          expiry_days:     deliverForm.expiryDays,
          language:        deliverForm.language,
        }),
      },
    )
    if (res.ok) {
      feedbackMsg.value      = t('adminReportTracking.deliverSuccess') || 'Rapport livré avec succès.'
      feedbackOk.value       = true
      showDeliverModal.value = false
      await loadDeliveries()
    } else {
      const json = await res.json().catch(() => ({}))
      feedbackMsg.value = json.error || (t('adminReportTracking.deliverFailed') || 'Échec de la livraison.')
      feedbackOk.value  = false
    }
  } catch (err) {
    feedbackMsg.value = String(err)
    feedbackOk.value  = false
  } finally {
    submittingDelivery.value = false
    setTimeout(() => { feedbackMsg.value = null }, 4000)
  }
}

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function statusLabel(status: string): string {
  const key = `adminReportTracking.status.${status}`
  return t(key) || status
}

function countryFlag(code: string): string {
  if (!code || code.length !== 2) return ''
  // Convertit le code pays en emoji drapeau (Regional Indicator Symbols)
  const codePoints = [...code.toUpperCase()].map(
    (c) => 0x1F1E6 - 65 + c.charCodeAt(0),
  )
  return String.fromCodePoint(...codePoints)
}

function truncateUa(ua: string | null): string {
  if (!ua) return '—'
  return ua.length > 60 ? ua.slice(0, 57) + '…' : ua
}

// ─── Init ────────────────────────────────────────────────────────────────────

onMounted(() => {
  loadDeliveries()
})
</script>

<style scoped>
/* ─── Layout ────────────────────────────────────────────────────────────────── */
.art-page {
  min-height: 100vh;
  background: var(--wi-background, #FAF7F2);
  color: var(--wi-text-primary, #241915);
  font-family: 'Outfit', 'Manrope', system-ui, sans-serif;
}

/* Topbar */
.art-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid rgba(36, 25, 21, 0.06);
  background: #fff;
}
.art-back {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--wi-text-primary, #241915);
}
.art-back-arrow { font-size: 16px; }
.art-topbar-right { display: flex; gap: 12px; }
.art-pill {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  border: 1.5px solid rgba(36, 25, 21, 0.15);
  color: var(--wi-text-primary, #241915);
  transition: background 0.15s;
}
.art-pill:hover { background: rgba(36, 25, 21, 0.04); }
.art-pill--ghost { background: transparent; }

/* Main */
.art-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 32px 80px;
}

/* Hero */
.art-hero { margin-bottom: 32px; }
.art-headline {
  font-size: 28px;
  font-weight: 700;
  color: var(--wi-text-primary, #241915);
  margin: 0 0 8px 0;
}
.art-sub {
  font-size: 15px;
  color: #57423a;
  margin: 0 0 6px 0;
}
.art-report-id {
  margin: 0;
  font-size: 13px;
  color: #888;
}
.art-report-id code {
  background: rgba(36, 25, 21, 0.06);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

/* Actions */
.art-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.art-btn {
  padding: 10px 20px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: background 0.15s, opacity 0.15s;
}
.art-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.art-btn--primary { background: var(--wi-accent, #a13f0f); color: #fff; }
.art-btn--primary:hover:not(:disabled) { background: #8b3309; }
.art-btn--secondary {
  background: transparent;
  border: 1.5px solid rgba(36, 25, 21, 0.2);
  color: var(--wi-text-primary, #241915);
}
.art-btn--secondary:hover:not(:disabled) { background: rgba(36, 25, 21, 0.04); }
.art-btn--ghost {
  background: transparent;
  border: 1.5px solid rgba(36, 25, 21, 0.15);
  color: #57423a;
}

/* State messages */
.art-state { color: #57423a; font-size: 15px; margin: 24px 0; }
.art-state--error { color: #c0392b; }
.art-state--muted { color: #a0a0a0; font-size: 13px; }

/* Table principale */
.art-table-card {
  background: #fff;
  border: 1px solid rgba(36, 25, 21, 0.08);
  border-radius: 12px;
  overflow: hidden;
}
.art-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.art-table thead th {
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: #57423a;
  background: #FAF7F2;
  border-bottom: 1px solid rgba(36, 25, 21, 0.08);
  text-align: left;
}
.art-row td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(36, 25, 21, 0.05);
  vertical-align: middle;
}
.art-row:last-child td { border-bottom: none; }
.art-row--expanded td { background: rgba(36, 25, 21, 0.02); }

.art-email { font-weight: 600; font-size: 14px; }
.art-name  { font-size: 12px; color: #57423a; }

.art-lang-badge {
  background: rgba(36, 25, 21, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.art-status-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.art-status-pill--sent     { background: #d4edda; color: #155724; }
.art-status-pill--pending  { background: #fff3cd; color: #856404; }
.art-status-pill--failed   { background: #f8d7da; color: #721c24; }
.art-status-pill--expired  { background: rgba(36, 25, 21, 0.08); color: #57423a; }
.art-status-pill--archived { background: rgba(36, 25, 21, 0.05); color: #888; }

.art-cell-date { font-size: 12px; color: #57423a; white-space: nowrap; }
.art-cell-count { text-align: center; }
.art-count-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-accent, #a13f0f);
  display: flex;
  align-items: center;
  gap: 4px;
}
.art-count-arrow { font-size: 10px; }

.art-cell-actions { text-align: right; }
.art-action {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1.5px solid rgba(36, 25, 21, 0.15);
  background: none;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: var(--wi-text-primary, #241915);
  transition: background 0.15s;
}
.art-action:hover:not(:disabled) { background: rgba(36, 25, 21, 0.05); }
.art-action:disabled { opacity: 0.5; cursor: not-allowed; }
.art-action--resend { color: var(--wi-accent, #a13f0f); border-color: var(--wi-accent, #a13f0f); }

/* Panel téléchargements */
.art-row--downloads td {
  padding: 0;
  background: rgba(36, 25, 21, 0.02);
}
.art-downloads-panel {
  padding: 20px 24px;
  border-top: 1px solid rgba(36, 25, 21, 0.08);
}
.art-downloads-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 14px 0;
  color: var(--wi-text-primary, #241915);
}
.art-downloads-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.art-downloads-table th {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #57423a;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(36, 25, 21, 0.08);
  text-align: left;
}
.art-dl-row td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(36, 25, 21, 0.05);
}
.art-dl-row:last-child td { border-bottom: none; }
.art-geo { font-weight: 600; }
.art-ip  { font-family: monospace; font-size: 12px; }
.art-ua  { font-size: 11px; color: #57423a; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Feedback */
.art-feedback {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 28px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 4px 24px rgba(0,0,0,0.12);
  z-index: 1000;
  white-space: nowrap;
}
.art-feedback--ok  { background: #d4edda; color: #155724; }
.art-feedback--err { background: #f8d7da; color: #721c24; }

/* Modal */
.art-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 16px;
}
.art-modal {
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.18);
  overflow: hidden;
}
.art-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(36, 25, 21, 0.06);
}
.art-modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--wi-text-primary, #241915);
}
.art-modal-close {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: #57423a;
  line-height: 1;
  padding: 0;
}
.art-modal-form { padding: 20px 24px; }
.art-field { margin-bottom: 16px; }
.art-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #3a2e29;
}
.art-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border: 1.5px solid rgba(36, 25, 21, 0.15);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
  background: #FAF7F2;
}
.art-input:focus { border-color: var(--wi-accent, #a13f0f); }

.art-lang-btns {
  display: flex;
  gap: 8px;
}
.art-lang-btn {
  padding: 6px 16px;
  border-radius: 999px;
  border: 1.5px solid rgba(36, 25, 21, 0.15);
  background: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  color: #3a2e29;
  letter-spacing: 0.08em;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.art-lang-btn--active {
  background: var(--wi-accent, #a13f0f);
  border-color: var(--wi-accent, #a13f0f);
  color: #fff;
}

.art-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(36, 25, 21, 0.06);
}
</style>
