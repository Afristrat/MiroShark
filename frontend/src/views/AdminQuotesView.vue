<template>
  <div class="aq-page">
    <header class="aq-topbar">
      <router-link to="/" class="aq-back" :title="$t('nav.homeTitle')">
        <span class="aq-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
      <div class="aq-topbar-right">
        <router-link
          to="/admin/analytics"
          class="aq-pill"
          :title="$t('nav.adminTitle')"
        >
{{ $t('nav.admin') }}
</router-link>
      </div>
    </header>

    <main class="aq-main">
      <section class="aq-hero">
        <h1 class="aq-headline">{{ $t('adminQuotes.title') }}</h1>
        <p class="aq-sub">{{ $t('adminQuotes.subtitle') }}</p>
      </section>

      <!-- Filtres -->
      <section class="aq-filters" :aria-label="$t('adminQuotes.filters.status')">
        <label class="aq-filter">
          <span class="aq-filter-label">{{ $t('adminQuotes.filters.status') }}</span>
          <select v-model="statusFilter" @change="loadQuotes">
            <option value="">{{ $t('adminQuotes.filters.all') }}</option>
            <option v-for="s in allStatuses" :key="s" :value="s">
              {{ $t(`adminQuotes.status.${s}`) }}
            </option>
          </select>
        </label>
        <button class="aq-reset" type="button" @click="resetFilters">
          {{ $t('adminQuotes.filters.reset') }}
        </button>
      </section>

      <!-- Loading / empty / error -->
      <p v-if="loading" class="aq-loading">{{ $t('adminQuotes.loading') }}</p>
      <p v-else-if="error" class="aq-error" role="alert">{{ error }}</p>
      <p v-else-if="quotes.length === 0" class="aq-empty">{{ $t('adminQuotes.empty') }}</p>

      <!-- Table -->
      <section v-else class="aq-table-wrap">
        <table class="aq-table">
          <thead>
            <tr>
              <th>{{ $t('adminQuotes.table.id') }}</th>
              <th>{{ $t('adminQuotes.table.date') }}</th>
              <th>{{ $t('adminQuotes.table.contact') }}</th>
              <th>{{ $t('adminQuotes.table.package') }}</th>
              <th>{{ $t('adminQuotes.table.situation') }}</th>
              <th>{{ $t('adminQuotes.table.status') }}</th>
              <th>{{ $t('adminQuotes.table.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="q in quotes" :key="q.quote_id">
              <td><code class="aq-id">{{ q.quote_id }}</code></td>
              <td>{{ formatDate(q.submitted_at || q.payload?.submitted_at) }}</td>
              <td>
                <div class="aq-contact">
                  <span class="aq-contact-name">{{ q.payload?.full_name || '—' }}</span>
                  <span class="aq-contact-email">{{ q.payload?.email || '—' }}</span>
                </div>
              </td>
              <td>{{ q.payload?.package || '—' }}</td>
              <td class="aq-situation">{{ truncate(q.payload?.message, 100) }}</td>
              <td>
                <span class="aq-pill" :class="`aq-pill--${q.status?.status}`">
                  {{ $t(`adminQuotes.status.${q.status?.status || 'received'}`) }}
                </span>
              </td>
              <td>
                <button class="aq-action" type="button" @click="openModal(q)">
                  {{ $t('common.viewDetails') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <!-- Modal détail -->
    <Teleport to="body">
      <div v-if="modal.open" class="aq-modal-overlay" @click.self="closeModal">
        <div class="aq-modal" role="dialog" :aria-label="$t('adminQuotes.modal.title')">
          <header class="aq-modal-header">
            <h3>{{ $t('adminQuotes.modal.title') }} · <code>{{ modal.quote?.quote_id }}</code></h3>
            <button class="aq-modal-close" type="button" @click="closeModal">{{ $t('adminQuotes.modal.close') }}</button>
          </header>

          <div class="aq-modal-body">
            <router-link
              v-if="modal.quote?.intake?.session_id"
              :to="{ name: 'Console', query: { intake_session_id: modal.quote.intake.session_id } }"
              class="aq-action"
              @click="closeModal"
            >
              {{ $t('adminQuotes.createSimulationFromQuote') }}
            </router-link>
            <!-- Payload dump -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.table.contact') }} / {{ $t('adminQuotes.table.situation') }}</h4>
              <dl class="aq-dl">
                <div><dt>Nom</dt><dd>{{ modal.quote?.payload?.full_name || '—' }}</dd></div>
                <div><dt>Email</dt><dd>{{ modal.quote?.payload?.email || '—' }}</dd></div>
                <div><dt>Société</dt><dd>{{ modal.quote?.payload?.company || '—' }}</dd></div>
                <div><dt>Rôle</dt><dd>{{ modal.quote?.payload?.role || '—' }}</dd></div>
                <div><dt>Téléphone</dt><dd>{{ modal.quote?.payload?.phone || '—' }}</dd></div>
                <div><dt>Package</dt><dd>{{ modal.quote?.payload?.package || '—' }}</dd></div>
                <div><dt>Volume / an</dt><dd>{{ modal.quote?.payload?.expected_simulations_per_year || '—' }}</dd></div>
                <div><dt>Échéance</dt><dd>{{ modal.quote?.payload?.target_deadline || '—' }}</dd></div>
                <div><dt>Industrie</dt><dd>{{ modal.quote?.payload?.industry || '—' }}</dd></div>
                <div><dt>Géo</dt><dd>{{ (modal.quote?.payload?.geo_focus || []).join(', ') || '—' }}</dd></div>
              </dl>
              <div class="aq-message">
                <h5>Message</h5>
                <p>{{ modal.quote?.payload?.message || '—' }}</p>
              </div>
            </section>

            <!-- Statut + transitions -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.table.status') }}</h4>
              <p>
                <span class="aq-pill" :class="`aq-pill--${currentStatus}`">
                  {{ $t(`adminQuotes.status.${currentStatus}`) }}
                </span>
              </p>
              <div class="aq-transitions">
                <button
                  v-for="next in allowedNextStatuses"
                  :key="next"
                  class="aq-transition-btn"
                  type="button"
                  :disabled="busy"
                  @click="onTransition(next)"
                >
                  → {{ $t(`adminQuotes.status.${next}`) }}
                </button>
              </div>
              <p v-if="transitionError" class="aq-error" role="alert">{{ transitionError }}</p>
            </section>

            <!-- Lien de paiement Stripe -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.modal.paymentLink') }}</h4>
              <input
                v-model="paymentLinkInput"
                class="aq-input"
                type="url"
                :placeholder="$t('adminQuotes.modal.paymentLinkPlaceholder')"
              />
              <textarea
                v-model="paymentMessage"
                class="aq-textarea"
                :placeholder="$t('adminQuotes.modal.notesPlaceholder')"
                rows="2"
              ></textarea>
              <button
                class="aq-cta"
                type="button"
                :disabled="busy || !paymentLinkInput.trim()"
                @click="onSendPaymentLink"
              >
{{ $t('adminQuotes.modal.sendPaymentLink') }}
</button>
              <p v-if="modal.quote?.status?.last_email_sent_at" class="aq-meta">
                {{ $t('adminQuotes.modal.sendPaymentLinkSent', { ago: formatDate(modal.quote.status.last_email_sent_at) }) }}
              </p>
            </section>

            <!-- Marquer livré -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.modal.markDelivered') }}</h4>
              <input
                v-model="deliveredUrlInput"
                class="aq-input"
                type="url"
                :placeholder="$t('adminQuotes.modal.deliveredAsk')"
              />
              <button
                class="aq-cta aq-cta--secondary"
                type="button"
                :disabled="busy || !deliveredUrlInput.trim()"
                @click="onSendDelivered"
              >
{{ $t('adminQuotes.modal.markDelivered') }}
</button>
            </section>

            <!-- Notes admin -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.modal.notes') }}</h4>
              <textarea
                v-model="notesInput"
                class="aq-textarea"
                rows="4"
                :placeholder="$t('adminQuotes.modal.notesPlaceholder')"
              ></textarea>
              <button
                class="aq-cta aq-cta--ghost"
                type="button"
                :disabled="busy"
                @click="onSaveNotes"
              >
{{ $t('adminQuotes.modal.saveNotes') }}
</button>
              <p v-if="notesMessage" class="aq-meta">{{ notesMessage }}</p>
            </section>

            <!-- Historique -->
            <section class="aq-modal-section">
              <h4>{{ $t('adminQuotes.modal.history') }}</h4>
              <ol class="aq-history">
                <li v-for="(h, idx) in (modal.quote?.status?.history || [])" :key="idx">
                  <span class="aq-pill" :class="`aq-pill--${h.status}`">
                    {{ $t(`adminQuotes.status.${h.status}`) }}
                  </span>
                  <span class="aq-meta">· {{ formatDate(h.at) }}</span>
                  <span v-if="h.by" class="aq-meta">· {{ h.by }}</span>
                  <p v-if="h.notes" class="aq-history-notes">{{ h.notes }}</p>
                </li>
              </ol>
            </section>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  fetchAdminQuotes,
  fetchAdminQuoteDetail,
  patchAdminQuoteStatus,
  patchAdminQuoteNotes,
  sendAdminQuotePaymentLink,
  sendAdminQuoteDelivered,
} from '../api/client'

const route = useRoute()

const allStatuses = [
  'received', 'reviewing', 'quoted', 'declined', 'paid', 'in_progress', 'delivered',
]

const ALLOWED_TRANSITIONS = {
  received: ['reviewing', 'declined'],
  reviewing: ['quoted', 'declined'],
  quoted: ['paid', 'declined'],
  paid: ['in_progress', 'declined'],
  in_progress: ['delivered', 'declined'],
  delivered: [],
  declined: [],
}

const quotes = ref([])
const loading = ref(false)
const error = ref('')
const statusFilter = ref('')

const modal = reactive({ open: false, quote: null })
const busy = ref(false)
const transitionError = ref('')
const paymentLinkInput = ref('')
const paymentMessage = ref('')
const deliveredUrlInput = ref('')
const notesInput = ref('')
const notesMessage = ref('')

const currentStatus = computed(() => modal.quote?.status?.status || 'received')
const allowedNextStatuses = computed(() => ALLOWED_TRANSITIONS[currentStatus.value] || [])

async function loadQuotes() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchAdminQuotes({
      limit: 100,
      offset: 0,
      status: statusFilter.value || undefined,
    })
    quotes.value = res?.data?.quotes || []
  } catch (err) {
    error.value = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  statusFilter.value = ''
  loadQuotes()
}

async function openModal(q) {
  modal.open = true
  modal.quote = q
  busy.value = false
  transitionError.value = ''
  paymentLinkInput.value = q.status?.payment_link || ''
  paymentMessage.value = ''
  deliveredUrlInput.value = q.status?.delivered_url || ''
  notesInput.value = q.status?.notes || ''
  notesMessage.value = ''
  // Re-fetch detail (sidecar peut avoir bougé entre liste et clic)
  try {
    const res = await fetchAdminQuoteDetail(q.quote_id)
    if (res?.data) {
      modal.quote = {
        quote_id: q.quote_id,
        payload: res.data.payload,
        status: res.data.status,
        submitted_at: q.submitted_at,
      }
      paymentLinkInput.value = res.data.status?.payment_link || ''
      deliveredUrlInput.value = res.data.status?.delivered_url || ''
      notesInput.value = res.data.status?.notes || ''
    }
  } catch (_) {
    // fail-soft : on garde les données de la liste
  }
}

function closeModal() {
  modal.open = false
  modal.quote = null
}

async function onTransition(nextStatus) {
  if (!modal.quote) return
  busy.value = true
  transitionError.value = ''
  try {
    const res = await patchAdminQuoteStatus(modal.quote.quote_id, {
      status: nextStatus,
    })
    if (res?.data?.status) {
      modal.quote = { ...modal.quote, status: res.data.status }
      // Update list
      const idx = quotes.value.findIndex(x => x.quote_id === modal.quote.quote_id)
      if (idx >= 0) {
        quotes.value[idx] = { ...quotes.value[idx], status: res.data.status }
      }
    }
  } catch (err) {
    transitionError.value = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    busy.value = false
  }
}

async function onSendPaymentLink() {
  if (!modal.quote) return
  busy.value = true
  transitionError.value = ''
  try {
    const res = await sendAdminQuotePaymentLink(modal.quote.quote_id, {
      payment_link: paymentLinkInput.value.trim(),
      custom_message: paymentMessage.value.trim() || undefined,
    })
    if (res?.data?.status) {
      modal.quote = { ...modal.quote, status: res.data.status }
      const idx = quotes.value.findIndex(x => x.quote_id === modal.quote.quote_id)
      if (idx >= 0) {
        quotes.value[idx] = { ...quotes.value[idx], status: res.data.status }
      }
    }
  } catch (err) {
    transitionError.value = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    busy.value = false
  }
}

async function onSendDelivered() {
  if (!modal.quote) return
  busy.value = true
  transitionError.value = ''
  try {
    const res = await sendAdminQuoteDelivered(modal.quote.quote_id, {
      delivered_url: deliveredUrlInput.value.trim(),
    })
    if (res?.data?.status) {
      modal.quote = { ...modal.quote, status: res.data.status }
      const idx = quotes.value.findIndex(x => x.quote_id === modal.quote.quote_id)
      if (idx >= 0) {
        quotes.value[idx] = { ...quotes.value[idx], status: res.data.status }
      }
    }
  } catch (err) {
    transitionError.value = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    busy.value = false
  }
}

async function onSaveNotes() {
  if (!modal.quote) return
  busy.value = true
  notesMessage.value = ''
  try {
    const res = await patchAdminQuoteNotes(modal.quote.quote_id, notesInput.value)
    if (res?.data?.status) {
      modal.quote = { ...modal.quote, status: res.data.status }
      notesMessage.value = 'Notes sauvegardées.'
    }
  } catch (err) {
    notesMessage.value = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    busy.value = false
  }
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString()
  } catch (_) {
    return iso
  }
}

function truncate(s, max) {
  if (!s) return '—'
  if (s.length <= max) return s
  return s.slice(0, max - 1).trimEnd() + '…'
}

onMounted(async () => {
  await loadQuotes()
  // Deep-link depuis la notif admin (ADR-IQ-15) : /admin/quotes?quote_id=…
  // ouvre directement la fiche de la demande. openModal re-fetch le détail,
  // donc un objet minimal { quote_id } suffit même si le devis n'est pas
  // dans la première page chargée.
  const deepLinkId = route.query.quote_id
  if (deepLinkId) {
    const match = quotes.value.find(q => q.quote_id === deepLinkId)
    openModal(match || { quote_id: deepLinkId })
  }
})
</script>

<style scoped>
.aq-page {
  min-height: 100vh;
  background: var(--wi-bg, #FAF7F2);
  font-family: var(--wi-font-body, 'Manrope', sans-serif);
  color: var(--wi-on-bg, #241915);
}

.aq-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-block-end: 1px solid var(--wi-outline-variant);
  background: var(--wi-surface);
}
.aq-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--wi-on-bg);
  font-weight: 600;
}
.aq-pill {
  padding: 6px 16px;
  border-radius: 999px;
  background: var(--wi-primary-soft);
  color: var(--wi-primary);
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.aq-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px;
}
.aq-hero { margin-bottom: 24px; }
.aq-headline {
  font-family: var(--wi-font-heading);
  font-size: 32px;
  margin: 0 0 8px 0;
}
.aq-sub {
  color: var(--wi-on-surface-variant);
  margin: 0;
}

.aq-filters {
  display: flex;
  align-items: end;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.aq-filter { display: flex; flex-direction: column; gap: 4px; }
.aq-filter-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--wi-on-surface-variant);
}
.aq-filter select {
  padding: 8px 12px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  background: var(--wi-surface);
  color: var(--wi-on-surface);
  font-family: inherit;
}
.aq-reset {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  color: var(--wi-on-surface);
  font-family: inherit;
}

.aq-loading, .aq-empty, .aq-error {
  text-align: center;
  padding: 48px 16px;
  color: var(--wi-on-surface-variant);
}
.aq-error { color: var(--wi-error); }

.aq-table-wrap {
  overflow-x: auto;
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: 12px;
}
.aq-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.aq-table thead {
  background: var(--wi-surface-container-low);
}
.aq-table th, .aq-table td {
  text-align: start;
  padding: 12px 16px;
  border-block-end: 1px solid var(--wi-outline-variant);
}
.aq-table th {
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--wi-on-surface-variant);
}
.aq-id { font-family: var(--ms-font-mono); font-size: 12px; }
.aq-contact { display: flex; flex-direction: column; gap: 2px; }
.aq-contact-name { font-weight: 600; }
.aq-contact-email {
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  font-family: var(--ms-font-mono);
}
.aq-situation {
  max-width: 320px;
  color: var(--wi-on-surface-variant);
}

.aq-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.aq-pill--received { background: rgba(36, 25, 21, 0.08); color: #57423a; }
.aq-pill--reviewing { background: rgba(33, 150, 243, 0.12); color: #0d47a1; }
.aq-pill--quoted { background: rgba(255, 133, 81, 0.18); color: #a13f0f; }
.aq-pill--declined { background: rgba(244, 67, 54, 0.12); color: #b71c1c; }
.aq-pill--paid { background: rgba(74, 200, 158, 0.18); color: #007a55; }
.aq-pill--in_progress { background: rgba(255, 99, 71, 0.18); color: #c93c1d; }
.aq-pill--delivered { background: rgba(76, 175, 80, 0.16); color: #1b5e20; }

.aq-action {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: none;
  border-radius: 999px;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.aq-action:hover { opacity: 0.9; }

/* Modal */
.aq-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(36, 25, 21, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 9999;
}
.aq-modal {
  background: var(--wi-surface);
  width: 720px;
  max-width: 100%;
  max-height: 90vh;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.aq-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-block-end: 1px solid var(--wi-outline-variant);
}
.aq-modal-header h3 { margin: 0; font-size: 16px; }
.aq-modal-close {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-family: inherit;
}
.aq-modal-body { padding: 24px; overflow-y: auto; flex: 1; }
.aq-modal-section { margin-bottom: 24px; }
.aq-modal-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-on-bg);
}
.aq-dl {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px 16px;
  margin: 0;
}
.aq-dl > div { display: flex; flex-direction: column; gap: 2px; }
.aq-dl dt {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  letter-spacing: 0.04em;
}
.aq-dl dd { margin: 0; font-size: 13px; }

.aq-message h5 { margin: 16px 0 4px 0; font-size: 12px; color: var(--wi-on-surface-variant); }
.aq-message p {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  white-space: pre-wrap;
}

.aq-transitions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.aq-transition-btn {
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
}
.aq-transition-btn:hover:not(:disabled) {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
}
.aq-transition-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.aq-input, .aq-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 8px;
  background: var(--wi-surface);
  font-family: inherit;
  font-size: 13px;
  margin-bottom: 8px;
  box-sizing: border-box;
}
.aq-textarea { resize: vertical; }

.aq-cta {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: none;
  border-radius: 999px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.aq-cta:disabled { opacity: 0.5; cursor: not-allowed; }
.aq-cta--secondary {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
}
.aq-cta--ghost {
  background: transparent;
  color: var(--wi-on-bg);
  border: 1px solid var(--wi-outline-variant);
}

.aq-meta {
  margin-top: 8px;
  font-size: 12px;
  color: var(--wi-on-surface-variant);
}

.aq-history {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.aq-history li {
  background: var(--wi-surface-container-low);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
}
.aq-history-notes {
  margin: 4px 0 0 0;
  font-style: italic;
  color: var(--wi-on-surface-variant);
}
</style>
