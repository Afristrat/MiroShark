<template>
  <div class="analytics-page" data-theme="dark">
    <!-- ───────────── Top bar ───────────── -->
    <header class="analytics-topbar">
      <router-link to="/" class="analytics-back" :title="$t('analytics.nav.backTitle')">
        <span class="analytics-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
      <div class="analytics-topbar-right">
        <router-link
          v-if="isSuperAdmin"
          to="/admin/quotes"
          class="analytics-pill"
          :title="$t('nav.adminQuotesTitle')"
          style="text-decoration:none"
        >
          {{ $t('nav.adminQuotes') }}
        </router-link>
        <span class="analytics-pill">
          <span class="analytics-pill-dot" aria-hidden="true"></span>
          {{ $t('analytics.opsBadge') }}
        </span>
      </div>
    </header>

    <main class="analytics-main">
      <!-- ───────────── US-100 — Gate super-admin ─────────────
           Plus de formulaire BASSIRA_ADMIN_TOKEN : on s'appuie 100 %
           sur l'auth Supabase + whitelist email. Si l'utilisateur
           n'est pas connecté → message + lien /login. S'il l'est mais
           sans privilège super-admin → message refus + retour /. -->
      <section v-if="!authed" class="analytics-gate" :aria-label="$t('analytics.gateSuperAdmin.aria')">
        <div class="analytics-gate-card">
          <h1 class="analytics-gate-title">{{ $t('analytics.gateSuperAdmin.title') }}</h1>
          <p class="analytics-gate-sub">
            {{ isAuthenticated
              ? $t('analytics.gateSuperAdmin.notSuperAdmin')
              : $t('analytics.gateSuperAdmin.notLoggedIn') }}
          </p>
          <div class="analytics-gate-actions">
            <router-link
              v-if="!isAuthenticated"
              :to="{ path: '/login', query: { redirect: '/admin/analytics' } }"
              class="analytics-gate-submit"
            >
              {{ $t('analytics.gateSuperAdmin.loginCta') }}
            </router-link>
            <router-link
              v-else
              to="/"
              class="analytics-gate-submit"
            >
              {{ $t('analytics.gateSuperAdmin.backHome') }}
            </router-link>
          </div>
        </div>
      </section>

      <!-- ───────────── Dashboard ───────────── -->
      <template v-else>
        <section class="analytics-hero">
          <h1 class="analytics-headline">{{ $t('analytics.title') }}</h1>
          <p class="analytics-sub">{{ $t('analytics.subtitle') }}</p>
        </section>

        <!-- Erreur réseau -->
        <section v-if="error && !loading" class="analytics-error" role="alert">
          <div class="analytics-error-icon" aria-hidden="true">!</div>
          <div class="analytics-error-body">
            <div class="analytics-error-title">{{ $t('analytics.error.title') }}</div>
            <div class="analytics-error-msg">{{ error }}</div>
          </div>
          <button class="analytics-error-retry" @click="fetchData">
            {{ $t('analytics.error.retry') }}
          </button>
        </section>

        <!-- Row 1 : KPI cards -->
        <section class="analytics-kpi-row" aria-label="KPIs">
          <article
            v-for="kpi in kpiCards"
            :key="kpi.key"
            class="analytics-kpi-card"
          >
            <div class="analytics-kpi-label">{{ kpi.label }}</div>
            <div class="analytics-kpi-value-row">
              <span class="analytics-kpi-value">
                <span v-if="loading && !data" class="analytics-skeleton analytics-kpi-skel"></span>
                <template v-else>{{ kpi.value }}</template>
              </span>
              <span
                v-if="!loading && kpi.trend"
                class="analytics-kpi-trend"
                :class="kpi.trend.cls"
              >
                <span class="analytics-kpi-trend-arrow" aria-hidden="true">{{ kpi.trend.arrow }}</span>
                {{ kpi.trend.text }}
              </span>
            </div>
          </article>
        </section>

        <!-- Row 2 : Funnel -->
        <section class="analytics-card" aria-label="Funnel">
          <header class="analytics-card-header">
            <h2 class="analytics-card-title">{{ $t('analytics.funnel.title') }}</h2>
            <span class="analytics-card-help">{{ $t('analytics.funnel.help') }}</span>
          </header>
          <div class="analytics-funnel">
            <div
              v-for="(step, idx) in funnelRows"
              :key="step.key"
              class="analytics-funnel-row"
            >
              <span class="analytics-funnel-label">{{ step.label }}</span>
              <div class="analytics-funnel-bar">
                <div
                  class="analytics-funnel-fill"
                  :style="{ width: step.widthPct + '%' }"
                  :class="{ 'analytics-funnel-fill--head': idx === 0 }"
                ></div>
              </div>
              <span class="analytics-funnel-value">{{ step.display }}</span>
            </div>
          </div>
        </section>

        <!-- Row 3 : Top packages + Time series -->
        <section class="analytics-row-double">
          <!-- Top packages -->
          <article class="analytics-card analytics-card--half">
            <header class="analytics-card-header">
              <h2 class="analytics-card-title">{{ $t('analytics.topPackages.title') }}</h2>
              <span class="analytics-card-help">{{ $t('analytics.topPackages.help') }}</span>
            </header>
            <div v-if="topPackages.length === 0 && !loading" class="analytics-empty">
              {{ $t('analytics.topPackages.empty') }}
            </div>
            <div v-else class="analytics-top-list">
              <div
                v-for="pkg in topPackagesNormalised"
                :key="pkg.package"
                class="analytics-top-row"
              >
                <span class="analytics-top-label" :title="pkg.package">{{ pkg.package }}</span>
                <div class="analytics-top-bar">
                  <div
                    class="analytics-top-fill"
                    :style="{ width: pkg.widthPct + '%' }"
                  ></div>
                </div>
                <span class="analytics-top-count">{{ pkg.n }}</span>
              </div>
            </div>
          </article>

          <!-- Time series 30d -->
          <article class="analytics-card analytics-card--half">
            <header class="analytics-card-header">
              <h2 class="analytics-card-title">{{ $t('analytics.timeSeries.title') }}</h2>
              <span class="analytics-card-help">{{ $t('analytics.timeSeries.help') }}</span>
            </header>
            <div class="analytics-series">
              <div class="analytics-series-bars">
                <div
                  v-for="day in timeSeriesNormalised"
                  :key="day.date"
                  class="analytics-series-bar-wrap"
                  :title="`${day.date} — ${day.completed}`"
                >
                  <div
                    class="analytics-series-bar"
                    :style="{ height: day.heightPct + '%' }"
                  ></div>
                </div>
              </div>
              <div class="analytics-series-axis">
                <span>{{ axisLabels.start }}</span>
                <span>{{ axisLabels.mid }}</span>
                <span>{{ axisLabels.end }}</span>
              </div>
            </div>
          </article>
        </section>

        <!-- ─────────── US-095 — Toutes les organisations (super-admin) ─────────── -->
        <section
          v-if="isSuperAdmin"
          class="analytics-card analytics-superadmin"
          aria-label="All organizations"
        >
          <header class="analytics-card-header">
            <h2 class="analytics-card-title">{{ $t('analytics.superAdmin.sectionTitle') }}</h2>
            <span class="analytics-card-help">{{ $t('analytics.superAdmin.sectionHelp') }}</span>
          </header>

          <div v-if="orgsLoading" class="analytics-empty">
            {{ $t('analytics.superAdmin.loading') }}
          </div>
          <div v-else-if="orgsError" class="analytics-empty" role="alert">
            {{ orgsError }}
          </div>
          <div v-else-if="organizations.length === 0" class="analytics-empty">
            {{ $t('analytics.superAdmin.empty') }}
          </div>
          <div v-else class="analytics-orgs-table-wrap">
            <table class="analytics-orgs-table">
              <thead>
                <tr>
                  <th>{{ $t('analytics.superAdmin.table.slug') }}</th>
                  <th>{{ $t('analytics.superAdmin.table.name') }}</th>
                  <th>{{ $t('analytics.superAdmin.table.sector') }}</th>
                  <th>{{ $t('analytics.superAdmin.table.country') }}</th>
                  <th>{{ $t('analytics.superAdmin.table.status') }}</th>
                  <th class="analytics-orgs-num">{{ $t('analytics.superAdmin.table.members') }}</th>
                  <th class="analytics-orgs-num">{{ $t('analytics.superAdmin.table.sims') }}</th>
                  <th class="analytics-orgs-num">{{ $t('analytics.superAdmin.table.published') }}</th>
                  <th class="analytics-orgs-num">{{ $t('analytics.superAdmin.table.avgBrier') }}</th>
                  <th>{{ $t('analytics.selfServiceToggle.column') }}</th>
                  <th>{{ $t('analytics.superAdmin.table.createdAt') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="org in organizations"
                  :key="org.id"
                  class="analytics-orgs-row"
                  :title="org.id"
                >
                  <td @click="openOrgDetail(org)"><span class="analytics-orgs-slug">{{ org.slug || '—' }}</span></td>
                  <td @click="openOrgDetail(org)">{{ org.name || '—' }}</td>
                  <td @click="openOrgDetail(org)">{{ org.sector || '—' }}</td>
                  <td @click="openOrgDetail(org)">{{ org.country_code || '—' }}</td>
                  <td @click="openOrgDetail(org)">
                    <span class="analytics-orgs-status" :class="`analytics-orgs-status--${org.status || 'unknown'}`">
                      {{ org.status || '—' }}
                    </span>
                  </td>
                  <td class="analytics-orgs-num" @click="openOrgDetail(org)">{{ org.members_count ?? '—' }}</td>
                  <td class="analytics-orgs-num" @click="openOrgDetail(org)">{{ org.simulations_count ?? '—' }}</td>
                  <td class="analytics-orgs-num" @click="openOrgDetail(org)">{{ org.published_count ?? '—' }}</td>
                  <td class="analytics-orgs-num" @click="openOrgDetail(org)">{{ formatBrier(org.avg_brier) }}</td>
                  <!-- US-098 — toggle self-service par org -->
                  <td>
                    <label class="analytics-ss-toggle" :title="$t('analytics.selfServiceToggle.help')">
                      <input
                        type="checkbox"
                        :checked="!!org.self_service_enabled"
                        :disabled="ssToggleLoading[org.id] === true"
                        @change.stop="toggleOrgSelfService(org)"
                        @click.stop
                      />
                      <span class="analytics-ss-toggle-text">
                        {{ org.self_service_enabled
                          ? $t('analytics.selfServiceToggle.on')
                          : $t('analytics.selfServiceToggle.off') }}
                      </span>
                    </label>
                  </td>
                  <td @click="openOrgDetail(org)">{{ formatDate(org.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ─────────── US-097 — Toutes les simulations cross-tenant ─────────── -->
        <section
          v-if="isSuperAdmin"
          class="analytics-card analytics-superadmin analytics-allsims"
          aria-label="All simulations"
        >
          <header class="analytics-card-header">
            <h2 class="analytics-card-title">{{ $t('analytics.allSims.sectionTitle') }}</h2>
            <span class="analytics-card-help">{{ $t('analytics.allSims.sectionHelp') }}</span>
          </header>

          <div class="analytics-allsims-filters">
            <label class="analytics-allsims-filter">
              <span class="analytics-allsims-filter-label">{{ $t('analytics.allSims.filters.org') }}</span>
              <select v-model="allSimsFilters.org_id" @change="loadAllSimulations(true)">
                <option value="">{{ $t('analytics.allSims.filters.allOrgs') }}</option>
                <option v-for="o in organizations" :key="o.id" :value="o.id">
                  {{ o.slug || o.name }}
                </option>
              </select>
            </label>
            <label class="analytics-allsims-filter">
              <span class="analytics-allsims-filter-label">{{ $t('analytics.allSims.filters.package') }}</span>
              <input
                v-model="allSimsFilters.package_id"
                type="text"
                :placeholder="$t('analytics.allSims.filters.packagePlaceholder')"
                @keyup.enter="loadAllSimulations(true)"
                @blur="loadAllSimulations(true)"
              />
            </label>
            <label class="analytics-allsims-filter">
              <span class="analytics-allsims-filter-label">{{ $t('analytics.allSims.filters.published') }}</span>
              <select v-model="allSimsFilters.published" @change="loadAllSimulations(true)">
                <option value="">{{ $t('analytics.allSims.filters.publishedAny') }}</option>
                <option value="true">{{ $t('analytics.allSims.filters.publishedYes') }}</option>
                <option value="false">{{ $t('analytics.allSims.filters.publishedNo') }}</option>
              </select>
            </label>
            <button
              type="button"
              class="analytics-allsims-reset"
              @click="resetAllSimsFilters"
            >
              {{ $t('analytics.allSims.filters.reset') }}
            </button>
          </div>

          <div v-if="allSimsLoading" class="analytics-empty">
            {{ $t('analytics.allSims.loading') }}
          </div>
          <div v-else-if="allSimsError" class="analytics-empty" role="alert">
            {{ allSimsError }}
          </div>
          <div v-else-if="allSimulations.length === 0" class="analytics-empty">
            {{ $t('analytics.allSims.empty') }}
          </div>
          <div v-else class="analytics-orgs-table-wrap">
            <table class="analytics-orgs-table">
              <thead>
                <tr>
                  <th>{{ $t('analytics.allSims.table.simulation') }}</th>
                  <th>{{ $t('analytics.allSims.table.org') }}</th>
                  <th>{{ $t('analytics.allSims.table.package') }}</th>
                  <th>{{ $t('analytics.allSims.table.published') }}</th>
                  <th>{{ $t('analytics.allSims.table.outcome') }}</th>
                  <th class="analytics-orgs-num">{{ $t('analytics.allSims.table.brier') }}</th>
                  <th>{{ $t('analytics.allSims.table.createdAt') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in allSimulations" :key="s.simulation_id" class="analytics-orgs-row" :title="s.simulation_id">
                  <td><span class="analytics-orgs-slug">{{ s.simulation_id?.slice(0, 8) }}…</span></td>
                  <td>
                    <span v-if="s.org_slug" class="analytics-orgs-slug">{{ s.org_slug }}</span>
                    <span v-else class="analytics-empty-inline">—</span>
                  </td>
                  <td>{{ s.package_id || '—' }}</td>
                  <td>
                    <span class="analytics-orgs-status" :class="s.is_published ? 'analytics-orgs-status--active' : 'analytics-orgs-status--unknown'">
                      {{ s.is_published ? $t('analytics.allSims.published.yes') : $t('analytics.allSims.published.no') }}
                    </span>
                  </td>
                  <td>{{ s.outcome?.label || '—' }}</td>
                  <td class="analytics-orgs-num">{{ formatBrier(s.brier_score) }}</td>
                  <td>{{ formatDate(s.created_at) }}</td>
                </tr>
              </tbody>
            </table>
            <div class="analytics-allsims-pagination">
              <button
                type="button"
                class="analytics-allsims-page-btn"
                :disabled="allSimsFilters.offset === 0 || allSimsLoading"
                @click="prevAllSimsPage"
              >
                ← {{ $t('analytics.allSims.pagination.prev') }}
              </button>
              <span class="analytics-allsims-page-info">
                {{ $t('analytics.allSims.pagination.range', {
                  from: allSimsFilters.offset + 1,
                  to: Math.min(allSimsFilters.offset + allSimulations.length, allSimsTotal),
                  total: allSimsTotal
                }) }}
              </span>
              <button
                type="button"
                class="analytics-allsims-page-btn"
                :disabled="allSimsFilters.offset + allSimulations.length >= allSimsTotal || allSimsLoading"
                @click="nextAllSimsPage"
              >
                {{ $t('analytics.allSims.pagination.next') }} →
              </button>
            </div>
          </div>
        </section>

        <!-- ─────────── Modal détail organisation ─────────── -->
        <div
          v-if="selectedOrg"
          class="analytics-org-modal"
          role="dialog"
          aria-modal="true"
          @click.self="closeOrgDetail"
        >
          <div class="analytics-org-modal-card">
            <header class="analytics-org-modal-header">
              <h3 class="analytics-org-modal-title">
                {{ selectedOrg.name || selectedOrg.slug || '—' }}
                <span class="analytics-org-modal-slug">{{ selectedOrg.slug }}</span>
              </h3>
              <button
                type="button"
                class="analytics-org-modal-close"
                :title="$t('analytics.superAdmin.detail.close')"
                @click="closeOrgDetail"
              >
                ×
              </button>
            </header>

            <div v-if="orgDetailLoading" class="analytics-empty">
              {{ $t('analytics.superAdmin.detail.loading') }}
            </div>
            <div v-else-if="orgDetailError" class="analytics-empty" role="alert">
              {{ orgDetailError }}
            </div>
            <div v-else class="analytics-org-modal-body">
              <!-- Members -->
              <section class="analytics-org-modal-section">
                <h4 class="analytics-org-modal-section-title">
                  {{ $t('analytics.superAdmin.detail.members') }}
                  <span class="analytics-org-modal-count">({{ orgDetail.members?.length ?? 0 }})</span>
                </h4>
                <div v-if="!orgDetail.members?.length" class="analytics-empty">
                  {{ $t('analytics.superAdmin.detail.noMembers') }}
                </div>
                <ul v-else class="analytics-org-modal-list">
                  <li v-for="m in orgDetail.members" :key="m.user_id">
                    <span class="analytics-org-modal-mono">{{ m.email || m.user_id }}</span>
                    <span class="analytics-org-modal-role">{{ m.role }}</span>
                  </li>
                </ul>
              </section>

              <!-- Simulations -->
              <section class="analytics-org-modal-section">
                <h4 class="analytics-org-modal-section-title">
                  {{ $t('analytics.superAdmin.detail.simulations') }}
                  <span class="analytics-org-modal-count">({{ orgDetail.simulations?.length ?? 0 }})</span>
                </h4>
                <div v-if="!orgDetail.simulations?.length" class="analytics-empty">
                  {{ $t('analytics.superAdmin.detail.noSims') }}
                </div>
                <ul v-else class="analytics-org-modal-list">
                  <li v-for="s in orgDetail.simulations" :key="s.simulation_id">
                    <span class="analytics-org-modal-mono">{{ s.simulation_id }}</span>
                    <span v-if="s.package_id" class="analytics-org-modal-pkg">{{ s.package_id }}</span>
                    <span v-if="s.is_published" class="analytics-org-modal-published">·published</span>
                    <span v-if="s.outcome?.label" class="analytics-org-modal-outcome">{{ s.outcome.label }}</span>
                    <span v-if="s.brier_score !== null && s.brier_score !== undefined" class="analytics-org-modal-brier">
                      Brier {{ Number(s.brier_score).toFixed(3) }}
                    </span>
                  </li>
                </ul>
              </section>
            </div>
          </div>
        </div>

        <p class="analytics-footer">
          {{ $t('analytics.footer', { date: lastFetchedLabel }) }}
        </p>
      </template>
    </main>
  </div>
</template>

<script setup>
/**
 * /admin/analytics — tableau de bord interne ops (US-065 + US-100).
 *
 * Audience : Amine + super-admins Bassira (whitelist email backend
 * BASSIRA_SUPER_ADMIN_EMAILS). Lecture en 30 secondes :
 *   - KPI row (4 chiffres bruts) — total / completed / 30d / quotes
 *   - Funnel (4 étapes : visits ? → simulations → completed → quotes)
 *   - Top packages (bar chart CSS, top 5 par template_id)
 *   - Time series 30 jours (bar chart CSS quotidien des completions)
 *   - US-095 : Toutes les organisations (cross-tenant, super-admin)
 *   - US-097 : Toutes les simulations (cross-tenant, super-admin)
 *
 * Auth (US-100) :
 *   - Plus de form sessionStorage admin token. La page s'appuie sur
 *     l'auth Supabase + whitelist email côté backend.
 *   - Si !auth.isAuthenticated → CTA Login (redirect=/admin/analytics).
 *   - Si auth mais !isSuperAdmin → message refus + retour /.
 *   - Si auth.isSuperAdmin → fetch direct /api/admin/analytics avec
 *     Bearer JWT (via api/client.js qui injecte le token).
 *
 * Le décorateur backend `@require_admin_token` accepte JWT super-admin
 * ou (transitionnellement) le legacy BASSIRA_ADMIN_TOKEN — à terme
 * (US-101+) seul le JWT sera accepté.
 */
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatApiError } from '../utils/error-handler'
import { useAuthStore } from '../stores/auth'
import {
  fetchAllOrganizations,
  fetchOrganizationDetail,
  fetchAllSimulations,
  setOrgSelfService,
} from '../api/client.js'
import client from '../api/client.js'

const { t } = useI18n()
const authStore = useAuthStore()

// ─── US-100 — Auth state via store Supabase + whitelist super-admin ────────
const isAuthenticated = computed(() => authStore.isAuthenticated)
const isSuperAdmin = computed(() => authStore.isSuperAdmin)
// Le tableau de bord est accessible UNIQUEMENT si super-admin confirmé.
const authed = computed(() => isAuthenticated.value && isSuperAdmin.value)

// ─── Data state ────────────────────────────────────────────────────────────
const data = ref(null)
const loading = ref(false)
const error = ref('')
const lastFetchedAt = ref(null)

// ─── API ───────────────────────────────────────────────────────────────────
const fetchData = async (silent = false) => {
  loading.value = true
  if (!silent) error.value = ''
  try {
    // US-100 — utilise le client axios qui injecte le Bearer JWT
    // automatiquement (cf. ../api/client.js interceptor). Plus besoin
    // de l'admin token sessionStorage.
    const res = await client.get('/api/admin/analytics')
    const payload = res && res.data !== undefined ? res.data : res
    data.value = payload
    lastFetchedAt.value = new Date()
  } catch (err) {
    error.value = formatApiError(err) || t('analytics.error.generic')
  } finally {
    loading.value = false
  }
}

// ─── US-095 — Super-admin (toutes les organisations) ───────────────────────
// `isSuperAdmin` est déjà déclaré plus haut (US-100 auth gate).
const organizations = ref([])
const orgsLoading = ref(false)
const orgsError = ref('')
const selectedOrg = ref(null)
const orgDetail = ref({ organization: null, members: [], simulations: [] })
const orgDetailLoading = ref(false)
const orgDetailError = ref('')

const loadAllOrganizations = async () => {
  orgsLoading.value = true
  orgsError.value = ''
  try {
    const res = await fetchAllOrganizations()
    // L'interceptor axios unwrappe déjà response.data → res est { success, data }.
    const payload = res?.data || res
    organizations.value = Array.isArray(payload?.organizations)
      ? payload.organizations
      : []
  } catch (err) {
    organizations.value = []
    orgsError.value = formatApiError(err) || t('analytics.superAdmin.error')
  } finally {
    orgsLoading.value = false
  }
}

const openOrgDetail = async (org) => {
  selectedOrg.value = org
  orgDetailLoading.value = true
  orgDetailError.value = ''
  orgDetail.value = { organization: null, members: [], simulations: [] }
  try {
    const res = await fetchOrganizationDetail(org.id)
    const payload = res?.data || res
    orgDetail.value = {
      organization: payload?.organization || null,
      members: Array.isArray(payload?.members) ? payload.members : [],
      simulations: Array.isArray(payload?.simulations) ? payload.simulations : [],
    }
  } catch (err) {
    orgDetailError.value =
      formatApiError(err) || t('analytics.superAdmin.detail.error')
  } finally {
    orgDetailLoading.value = false
  }
}

const closeOrgDetail = () => {
  selectedOrg.value = null
  orgDetail.value = { organization: null, members: [], simulations: [] }
  orgDetailError.value = ''
}

const formatBrier = (b) => {
  if (b === null || b === undefined) return '—'
  const n = Number(b)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(3)
}

const formatDate = (iso) => {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toISOString().slice(0, 10)
  } catch {
    return '—'
  }
}

// ─── US-098 — Toggle self_service_enabled par org ──────────────────────────
const ssToggleLoading = ref({}) // { [orgId]: boolean }

const toggleOrgSelfService = async (org) => {
  if (!org?.id) return
  const newValue = !org.self_service_enabled
  ssToggleLoading.value = { ...ssToggleLoading.value, [org.id]: true }
  try {
    const res = await setOrgSelfService(org.id, newValue)
    const payload = res?.data || res
    // Mise à jour optimiste de la ligne dans la liste.
    const idx = organizations.value.findIndex((o) => o.id === org.id)
    if (idx !== -1) {
      organizations.value[idx] = {
        ...organizations.value[idx],
        self_service_enabled: !!payload?.self_service_enabled,
      }
    }
  } catch (err) {
    // Ne change pas l'état visuel (la valeur reste celle d'avant), affiche
    // l'erreur dans la zone d'erreur globale orgsError.
    orgsError.value = formatApiError(err) || t('analytics.selfServiceToggle.error')
  } finally {
    const next = { ...ssToggleLoading.value }
    delete next[org.id]
    ssToggleLoading.value = next
  }
}

// ─── US-097 — Toutes les simulations cross-tenant ──────────────────────────
const allSimsPageSize = 50
const allSimsFilters = ref({
  org_id: '',
  package_id: '',
  published: '',
  offset: 0
})
const allSimulations = ref([])
const allSimsTotal = ref(0)
const allSimsLoading = ref(false)
const allSimsError = ref('')

const _normalisedFilters = () => {
  const f = allSimsFilters.value
  const payload = { limit: allSimsPageSize, offset: f.offset }
  if (f.org_id) payload.org_id = f.org_id
  if (f.package_id) payload.package_id = f.package_id.trim()
  if (f.published === 'true') payload.published = true
  if (f.published === 'false') payload.published = false
  return payload
}

const loadAllSimulations = async (resetOffset = false) => {
  if (resetOffset) {
    allSimsFilters.value.offset = 0
  }
  allSimsLoading.value = true
  allSimsError.value = ''
  try {
    const res = await fetchAllSimulations(_normalisedFilters())
    const payload = res?.data || res
    allSimulations.value = Array.isArray(payload?.simulations) ? payload.simulations : []
    allSimsTotal.value = typeof payload?.total === 'number' ? payload.total : allSimulations.value.length
  } catch (err) {
    allSimulations.value = []
    allSimsTotal.value = 0
    allSimsError.value = formatApiError(err) || t('analytics.allSims.error')
  } finally {
    allSimsLoading.value = false
  }
}

const prevAllSimsPage = () => {
  const next = Math.max(0, allSimsFilters.value.offset - allSimsPageSize)
  allSimsFilters.value.offset = next
  loadAllSimulations(false)
}

const nextAllSimsPage = () => {
  allSimsFilters.value.offset = allSimsFilters.value.offset + allSimsPageSize
  loadAllSimulations(false)
}

const resetAllSimsFilters = () => {
  allSimsFilters.value = { org_id: '', package_id: '', published: '', offset: 0 }
  loadAllSimulations(false)
}

onMounted(async () => {
  // US-100 — vérifie d'abord le flag super-admin avant de charger quoi que ce soit.
  if (authStore.isAuthenticated && !authStore.superAdminLoaded) {
    try {
      await authStore.fetchSuperStatus()
    } catch {
      /* fail-soft */
    }
  }
  // Si super-admin → charge dashboard + cross-tenant.
  if (authed.value) {
    fetchData()
    if (authStore.isSuperAdmin) {
      await loadAllOrganizations()
      // US-097 — charger la liste cross-tenant des simulations en parallèle
      loadAllSimulations(false)
    }
  }
})

// ─── KPI cards ─────────────────────────────────────────────────────────────
const kpiCards = computed(() => {
  const k = (data.value && data.value.kpis) || {}
  // Trend chips : seul "30 derniers jours" est marqué « positif » quand
  // le chiffre est non-nul (signal d'activité). On évite d'inventer des
  // pourcentages qu'on n'a pas — l'audience est interne, l'honnêteté
  // prime sur l'esthétique.
  const trendUp = (n) =>
    n > 0
      ? { cls: 'analytics-kpi-trend--up', arrow: '↑', text: t('analytics.kpi.trend.active') }
      : null
  return [
    {
      key: 'total',
      label: t('analytics.kpi.total'),
      value: k.total ?? 0,
      trend: null,
    },
    {
      key: 'completed',
      label: t('analytics.kpi.completed'),
      value: k.completed ?? 0,
      trend: trendUp(k.completed ?? 0),
    },
    {
      key: 'last_30d',
      label: t('analytics.kpi.last30d'),
      value: k.last_30d ?? 0,
      trend: trendUp(k.last_30d ?? 0),
    },
    {
      key: 'quotes',
      label: t('analytics.kpi.quotes'),
      value: k.quotes ?? 0,
      trend: trendUp(k.quotes ?? 0),
    },
  ]
})

// ─── Funnel ────────────────────────────────────────────────────────────────
const funnelRows = computed(() => {
  const steps = (data.value && data.value.funnel) || []
  // Echelle : on prend le max non-null. Si tout est null/0, les barres
  // restent à 4% pour rester visibles à vide.
  const numericValues = steps
    .map((s) => (typeof s.n === 'number' ? s.n : 0))
    .filter((n) => n > 0)
  const max = numericValues.length ? Math.max(...numericValues) : 1
  return steps.map((s) => {
    const n = typeof s.n === 'number' ? s.n : null
    const widthPct = n === null ? 4 : Math.max(4, Math.round((n / max) * 100))
    const display = n === null ? '—' : String(n)
    return {
      key: s.step,
      label: t(`analytics.funnel.steps.${s.step}`, s.step),
      widthPct,
      display,
    }
  })
})

// ─── Top packages ──────────────────────────────────────────────────────────
const topPackages = computed(() => (data.value && data.value.top_packages) || [])
const topPackagesNormalised = computed(() => {
  const list = topPackages.value
  if (list.length === 0) return []
  const max = Math.max(...list.map((p) => p.n || 0), 1)
  return list.map((p) => ({
    package: p.package,
    n: p.n,
    widthPct: Math.max(6, Math.round((p.n / max) * 100)),
  }))
})

// ─── Time series 30d ───────────────────────────────────────────────────────
const timeSeriesNormalised = computed(() => {
  const series = (data.value && data.value.time_series) || []
  const max = Math.max(...series.map((d) => d.completed || 0), 1)
  return series.map((d) => ({
    date: d.date,
    completed: d.completed,
    // Hauteur min 4% pour qu'une barre vide reste cliquable au survol.
    heightPct: d.completed === 0 ? 4 : Math.max(8, Math.round((d.completed / max) * 100)),
  }))
})

const axisLabels = computed(() => {
  const series = timeSeriesNormalised.value
  if (series.length === 0) {
    return { start: '', mid: '', end: '' }
  }
  const fmt = (iso) => {
    if (!iso) return ''
    const [, mm, dd] = iso.split('-')
    return `${dd}/${mm}`
  }
  return {
    start: fmt(series[0].date),
    mid: fmt(series[Math.floor(series.length / 2)].date),
    end: fmt(series[series.length - 1].date),
  }
})

const lastFetchedLabel = computed(() => {
  if (!lastFetchedAt.value) return '—'
  const d = lastFetchedAt.value
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════════════
   /admin/analytics — surface ops dark-mode.
   Tokens utilisés : --wi-* (mode dark forcé via data-theme="dark") + --ms-*
   pour les semantic colors (mint succès, rose erreur).
   ═══════════════════════════════════════════════════════════════════════════ */

.analytics-page {
  min-height: 100vh;
  background: #0f1117;
  color: var(--wi-on-bg);
  font-family: var(--wi-font-body);
  padding-bottom: var(--wi-space-xl);
}

/* ── Top bar ─────────────────────────────────────────────────────────────── */
.analytics-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wi-space-md) var(--wi-space-lg);
  border-bottom: 1px solid var(--wi-outline-variant);
  background: #1a1d27;
  position: sticky;
  top: 0;
  z-index: 10;
}

.analytics-back {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-xs);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: var(--wi-body-md);
  color: var(--wi-on-bg);
  text-decoration: none;
  transition: color 0.18s ease;
}
.analytics-back:hover { color: var(--ms-orange); }
.analytics-back-arrow { font-size: 18px; line-height: 1; }

.analytics-topbar-right {
  display: inline-flex;
  align-items: center;
  gap: var(--wi-space-sm);
}

.analytics-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill);
  background: rgba(127, 216, 166, 0.10);
  border: 1px solid rgba(127, 216, 166, 0.25);
  color: var(--ms-mint);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.analytics-pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ms-mint);
  box-shadow: 0 0 0 3px rgba(127, 216, 166, 0.18);
}

.analytics-logout {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  padding: 6px 12px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.analytics-logout:hover {
  border-color: var(--ms-rose);
  color: var(--ms-rose);
}

/* ── Layout ──────────────────────────────────────────────────────────────── */
.analytics-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--wi-space-xl) var(--wi-space-lg);
}

/* ── Auth gate ───────────────────────────────────────────────────────────── */
.analytics-gate {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.analytics-gate-card {
  width: 100%;
  max-width: 420px;
  background: #1a1d27;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-lg);
  box-shadow: var(--wi-shadow-lg);
}
.analytics-gate-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  margin: 0 0 var(--wi-space-xs);
  color: var(--wi-on-bg);
}
.analytics-gate-sub {
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  margin: 0 0 var(--wi-space-md);
}
.analytics-gate-form {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}
.analytics-gate-label {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
}
.analytics-gate-input {
  background: #0f1117;
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-bg);
  padding: 12px 14px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--ms-font-mono);
  font-size: var(--wi-body-md);
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.analytics-gate-input:focus {
  border-color: var(--ms-orange);
  box-shadow: 0 0 0 3px rgba(255, 133, 81, 0.18);
}
.analytics-gate-submit {
  margin-top: var(--wi-space-sm);
  background: var(--ms-orange);
  color: var(--ms-text-on-color);
  border: none;
  padding: 12px 18px;
  border-radius: var(--wi-radius-interactive);
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-md);
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  text-align: center;
  transition: background 0.18s ease, transform 0.18s ease;
}
.analytics-gate-submit:hover {
  background: var(--ms-orange-strong);
  transform: translateY(-1px);
}
/* US-100 — actions wrapper pour bouton login / retour home */
.analytics-gate-actions {
  display: flex;
  justify-content: center;
  margin-block-start: var(--wi-space-md);
}
.analytics-gate-error {
  margin-top: var(--wi-space-sm);
  padding: 10px 12px;
  background: rgba(244, 132, 122, 0.10);
  border: 1px solid rgba(244, 132, 122, 0.30);
  border-radius: var(--wi-radius-md);
  color: var(--ms-rose);
  font-size: var(--wi-caption);
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.analytics-hero { margin-bottom: var(--wi-space-lg); }
.analytics-headline {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  font-weight: var(--wi-h1-weight);
  line-height: var(--wi-h1-leading);
  letter-spacing: var(--wi-h1-tracking);
  margin: 0 0 var(--wi-space-xs);
  color: var(--wi-on-bg);
}
.analytics-sub {
  font-size: var(--wi-body-lg);
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* ── Error banner ────────────────────────────────────────────────────────── */
.analytics-error {
  display: flex;
  align-items: center;
  gap: var(--wi-space-sm);
  padding: var(--wi-space-sm) var(--wi-space-md);
  margin-bottom: var(--wi-space-md);
  background: rgba(244, 132, 122, 0.08);
  border: 1px solid rgba(244, 132, 122, 0.25);
  border-radius: var(--wi-radius-md);
}
.analytics-error-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(244, 132, 122, 0.18);
  color: var(--ms-rose);
  font-weight: 700;
}
.analytics-error-body { flex: 1; }
.analytics-error-title {
  font-weight: 600;
  color: var(--wi-on-bg);
}
.analytics-error-msg {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.analytics-error-retry {
  background: transparent;
  border: 1px solid var(--ms-rose);
  color: var(--ms-rose);
  padding: 6px 12px;
  border-radius: var(--wi-radius-interactive);
  font-size: var(--wi-caption);
  font-weight: 600;
  cursor: pointer;
}

/* ── KPI row ─────────────────────────────────────────────────────────────── */
.analytics-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--wi-space-sm);
  margin-bottom: var(--wi-space-md);
}
@media (max-width: 900px) {
  .analytics-kpi-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 540px) {
  .analytics-kpi-row { grid-template-columns: 1fr; }
}
.analytics-kpi-card {
  background: #1a1d27;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  transition: border-color 0.18s ease, transform 0.18s ease;
}
.analytics-kpi-card:hover {
  border-color: rgba(255, 133, 81, 0.35);
  transform: translateY(-2px);
}
.analytics-kpi-label {
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  margin-bottom: var(--wi-space-xs);
}
.analytics-kpi-value-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--wi-space-xs);
}
.analytics-kpi-value {
  font-family: var(--wi-font-heading);
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--wi-on-bg);
  font-variant-numeric: tabular-nums;
}
.analytics-kpi-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  font-weight: 600;
}
.analytics-kpi-trend--up { color: var(--ms-mint); }
.analytics-kpi-trend-arrow { font-size: 12px; }

.analytics-kpi-skel {
  display: inline-block;
  width: 80px;
  height: 36px;
  border-radius: var(--wi-radius-sm);
}
.analytics-skeleton {
  background: linear-gradient(90deg, #22263a 0%, #2a2f45 50%, #22263a 100%);
  background-size: 200% 100%;
  animation: analyticsShimmer 1.4s infinite linear;
}
@keyframes analyticsShimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Card primitive ──────────────────────────────────────────────────────── */
.analytics-card {
  background: #1a1d27;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  padding: var(--wi-space-md);
  margin-bottom: var(--wi-space-md);
}
.analytics-card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--wi-space-sm);
  gap: var(--wi-space-xs);
  flex-wrap: wrap;
}
.analytics-card-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  line-height: var(--wi-h3-leading);
  margin: 0;
  color: var(--wi-on-bg);
}
.analytics-card-help {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.analytics-empty {
  padding: var(--wi-space-md) 0;
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
  text-align: center;
}

/* ── Funnel ──────────────────────────────────────────────────────────────── */
.analytics-funnel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.analytics-funnel-row {
  display: grid;
  grid-template-columns: 140px 1fr 80px;
  align-items: center;
  gap: var(--wi-space-sm);
}
@media (max-width: 720px) {
  .analytics-funnel-row { grid-template-columns: 100px 1fr 60px; }
}
.analytics-funnel-label {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.analytics-funnel-bar {
  height: 36px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: var(--wi-radius-sm);
  overflow: hidden;
}
.analytics-funnel-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ms-orange) 0%, rgba(255, 133, 81, 0.55) 100%);
  border-radius: var(--wi-radius-sm);
  transition: width 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}
.analytics-funnel-fill--head {
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0.06) 100%);
}
.analytics-funnel-value {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-body-md);
  color: var(--wi-on-bg);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* ── Row 3 : double layout ───────────────────────────────────────────────── */
.analytics-row-double {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wi-space-md);
}
@media (max-width: 900px) {
  .analytics-row-double { grid-template-columns: 1fr; }
}
.analytics-card--half {
  margin-bottom: 0;
}

/* ── Top packages list ───────────────────────────────────────────────────── */
.analytics-top-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.analytics-top-row {
  display: grid;
  grid-template-columns: minmax(120px, 30%) 1fr 40px;
  align-items: center;
  gap: var(--wi-space-xs);
}
.analytics-top-label {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-bg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.analytics-top-bar {
  height: 12px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: var(--wi-radius-pill);
  overflow: hidden;
}
.analytics-top-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ms-mint) 0%, rgba(127, 216, 166, 0.45) 100%);
  border-radius: var(--wi-radius-pill);
  transition: width 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}
.analytics-top-count {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* ── Time series 30d ─────────────────────────────────────────────────────── */
.analytics-series {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-xs);
}
.analytics-series-bars {
  display: grid;
  grid-template-columns: repeat(30, 1fr);
  gap: 3px;
  height: 140px;
  align-items: end;
}
.analytics-series-bar-wrap {
  height: 100%;
  display: flex;
  align-items: flex-end;
}
.analytics-series-bar {
  width: 100%;
  background: linear-gradient(180deg, var(--ms-orange) 0%, rgba(255, 133, 81, 0.55) 100%);
  border-radius: 2px 2px 0 0;
  transition: height 0.36s cubic-bezier(0.22, 1, 0.36, 1);
}
.analytics-series-axis {
  display: flex;
  justify-content: space-between;
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.analytics-footer {
  margin-top: var(--wi-space-md);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  text-align: right;
}

/* ── US-095 — Super-admin section : « Toutes les organisations » ────────── */
.analytics-superadmin {
  /* La carte hérite de .analytics-card — on rajoute juste un petit
     liseré chaud pour signaler qu'il s'agit d'une vue privilégiée. */
  border-color: rgba(255, 133, 81, 0.30);
  box-shadow: 0 0 0 1px rgba(255, 133, 81, 0.06);
}
.analytics-orgs-table-wrap {
  overflow-x: auto;
  margin-block-start: var(--wi-space-xs);
}
.analytics-orgs-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.analytics-orgs-table thead th {
  text-align: start;
  padding: 8px 10px;
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--wi-on-surface-variant);
  border-block-end: 1px solid var(--wi-outline-variant);
  background: rgba(255, 255, 255, 0.02);
  white-space: nowrap;
}
.analytics-orgs-table tbody td {
  padding: 10px;
  border-block-end: 1px solid rgba(255, 255, 255, 0.04);
  color: var(--wi-on-bg);
  white-space: nowrap;
}
.analytics-orgs-num {
  text-align: end;
  font-family: var(--ms-font-mono);
  font-variant-numeric: tabular-nums;
}
.analytics-orgs-row {
  cursor: pointer;
  transition: background 0.18s ease;
}
.analytics-orgs-row:hover {
  background: rgba(255, 133, 81, 0.08);
}
.analytics-orgs-slug {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--ms-orange);
  background: rgba(255, 133, 81, 0.10);
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
}
.analytics-orgs-status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--wi-radius-pill);
  font-size: var(--wi-caption);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.analytics-orgs-status--active {
  color: var(--ms-mint);
  background: rgba(127, 216, 166, 0.12);
}
.analytics-orgs-status--trial {
  color: #f0c674;
  background: rgba(240, 198, 116, 0.12);
}
.analytics-orgs-status--suspended {
  color: var(--ms-rose);
  background: rgba(244, 132, 122, 0.12);
}
.analytics-orgs-status--unknown {
  color: var(--wi-on-surface-variant);
  background: rgba(255, 255, 255, 0.05);
}

/* ── Modal détail organisation ───────────────────────────────────────────── */
.analytics-org-modal {
  position: fixed;
  inset: 0;
  background: rgba(7, 9, 14, 0.78);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 1500;
  padding: var(--wi-space-md);
  animation: analyticsModalFadeIn 0.18s ease-out;
}
@keyframes analyticsModalFadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.analytics-org-modal-card {
  background: #1a1d27;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-card);
  width: 100%;
  max-width: 720px;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
  padding: var(--wi-space-md);
  box-shadow: var(--wi-shadow-lg);
}
.analytics-org-modal-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--wi-space-sm);
  margin-block-end: var(--wi-space-sm);
  padding-block-end: var(--wi-space-xs);
  border-block-end: 1px solid var(--wi-outline-variant);
}
.analytics-org-modal-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  margin: 0;
  color: var(--wi-on-bg);
}
.analytics-org-modal-slug {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--ms-orange);
  margin-inline-start: 8px;
}
.analytics-org-modal-close {
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  color: var(--wi-on-surface-variant);
  width: 32px;
  height: 32px;
  border-radius: var(--wi-radius-md);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.18s ease;
}
.analytics-org-modal-close:hover {
  border-color: var(--ms-rose);
  color: var(--ms-rose);
}
.analytics-org-modal-body {
  display: flex;
  flex-direction: column;
  gap: var(--wi-space-md);
}
.analytics-org-modal-section-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-body-md);
  font-weight: 600;
  margin: 0 0 var(--wi-space-xs);
  color: var(--wi-on-bg);
}
.analytics-org-modal-count {
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-weight: 400;
  margin-inline-start: 6px;
}
.analytics-org-modal-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: var(--wi-caption);
}
.analytics-org-modal-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--wi-radius-sm);
}
.analytics-org-modal-mono {
  font-family: var(--ms-font-mono);
  color: var(--wi-on-bg);
}
.analytics-org-modal-role {
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  background: rgba(255, 133, 81, 0.10);
  color: var(--ms-orange);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.analytics-org-modal-pkg {
  padding: 2px 8px;
  border-radius: var(--wi-radius-pill);
  background: rgba(127, 216, 166, 0.08);
  color: var(--ms-mint);
  font-size: 10px;
  font-family: var(--ms-font-mono);
}
.analytics-org-modal-published {
  color: var(--ms-mint);
  font-size: 10px;
  font-weight: 600;
}
.analytics-org-modal-outcome {
  color: var(--wi-on-surface-variant);
  font-size: var(--wi-caption);
}
.analytics-org-modal-brier {
  color: var(--wi-on-surface-variant);
  font-family: var(--ms-font-mono);
  font-size: var(--wi-caption);
}

/* ── US-098 — Toggle self-service par org ──────────────────────────────── */
.analytics-ss-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  user-select: none;
}
.analytics-ss-toggle input[type="checkbox"] {
  appearance: none;
  -webkit-appearance: none;
  width: 32px;
  height: 18px;
  border-radius: 9px;
  background: var(--wi-outline-variant);
  position: relative;
  cursor: pointer;
  transition: background var(--ms-transition, 180ms) var(--ms-ease, ease);
  flex-shrink: 0;
}
.analytics-ss-toggle input[type="checkbox"]::before {
  content: '';
  position: absolute;
  inset-block-start: 2px;
  inset-inline-start: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--wi-surface);
  transition: transform var(--ms-transition, 180ms) var(--ms-ease, ease);
}
.analytics-ss-toggle input[type="checkbox"]:checked {
  background: var(--wi-primary);
}
.analytics-ss-toggle input[type="checkbox"]:checked::before {
  transform: translateX(14px);
}
[dir="rtl"] .analytics-ss-toggle input[type="checkbox"]:checked::before {
  transform: translateX(-14px);
}
.analytics-ss-toggle input[type="checkbox"]:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.analytics-ss-toggle-text {
  white-space: nowrap;
}

/* ── US-097 — Toutes les simulations cross-tenant ───────────────────────── */
.analytics-allsims-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wi-space-md, 12px);
  align-items: flex-end;
  padding: var(--wi-space-sm, 8px) 0 var(--wi-space-md, 12px);
  border-block-end: 1px solid var(--wi-outline-variant);
  margin-block-end: var(--wi-space-md, 12px);
}
.analytics-allsims-filter {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 160px;
}
.analytics-allsims-filter-label {
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.analytics-allsims-filter select,
.analytics-allsims-filter input {
  padding: 6px 10px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-body);
  color: var(--wi-on-surface);
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-md);
  transition: border-color var(--ms-transition, 180ms) var(--ms-ease, ease);
}
.analytics-allsims-filter select:focus,
.analytics-allsims-filter input:focus {
  border-color: var(--wi-primary);
  outline: 2px solid var(--wi-primary-soft);
  outline-offset: 1px;
}
.analytics-allsims-reset {
  padding: 6px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-primary);
  background: transparent;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: all var(--ms-transition, 180ms) var(--ms-ease, ease);
}
.analytics-allsims-reset:hover {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
}
.analytics-allsims-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-md, 12px);
  padding: var(--wi-space-md, 12px) 0 0;
  border-block-start: 1px solid var(--wi-outline-variant);
  margin-block-start: var(--wi-space-md, 12px);
}
.analytics-allsims-page-btn {
  padding: 6px 14px;
  font-family: var(--wi-font-body);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface);
  background: var(--wi-surface-container-low);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  cursor: pointer;
  transition: all var(--ms-transition, 180ms) var(--ms-ease, ease);
}
.analytics-allsims-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.analytics-allsims-page-btn:not(:disabled):hover {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
}
.analytics-allsims-page-info {
  font-family: var(--ms-font-mono, monospace);
  font-size: var(--wi-caption);
  color: var(--wi-on-surface-variant);
}
.analytics-empty-inline {
  color: var(--wi-on-surface-variant);
  font-style: italic;
}

/* ── RTL support ─────────────────────────────────────────────────────────── */
[dir="rtl"] .analytics-back-arrow { transform: scaleX(-1); }
[dir="rtl"] .analytics-funnel-fill,
[dir="rtl"] .analytics-top-fill {
  background: linear-gradient(270deg, var(--ms-orange) 0%, rgba(255, 133, 81, 0.55) 100%);
}
</style>
