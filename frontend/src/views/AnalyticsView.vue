<template>
  <div class="analytics-page" data-theme="dark">
    <!-- ───────────── Top bar ───────────── -->
    <header class="analytics-topbar">
      <router-link to="/" class="analytics-back" :title="$t('analytics.nav.backTitle')">
        <span class="analytics-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') }}</span>
      </router-link>
      <div class="analytics-topbar-right">
        <span class="analytics-pill">
          <span class="analytics-pill-dot" aria-hidden="true"></span>
          {{ $t('analytics.opsBadge') }}
        </span>
        <button
          v-if="authed"
          type="button"
          class="analytics-logout"
          :title="$t('analytics.logout')"
          @click="logout"
        >
          {{ $t('analytics.logout') }}
        </button>
      </div>
    </header>

    <main class="analytics-main">
      <!-- ───────────── Auth gate ─────────────
           Quand le token n'est pas en sessionStorage on remplace
           tout le contenu par un formulaire. Pas de redirect — c'est
           une vue ops, l'opérateur attendu sait pourquoi il est là. -->
      <section v-if="!authed" class="analytics-gate" aria-label="Admin auth">
        <div class="analytics-gate-card">
          <h1 class="analytics-gate-title">{{ $t('analytics.gate.title') }}</h1>
          <p class="analytics-gate-sub">{{ $t('analytics.gate.subtitle') }}</p>
          <form class="analytics-gate-form" @submit.prevent="login">
            <label class="analytics-gate-label" for="analytics-token-input">
              {{ $t('analytics.gate.label') }}
            </label>
            <input
              id="analytics-token-input"
              v-model="tokenInput"
              type="password"
              class="analytics-gate-input"
              :placeholder="$t('analytics.gate.placeholder')"
              autocomplete="off"
              required
            />
            <button type="submit" class="analytics-gate-submit">
              {{ $t('analytics.gate.submit') }}
            </button>
          </form>
          <p v-if="gateError" class="analytics-gate-error" role="alert">
            {{ gateError }}
          </p>
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
                  v-for="(day, idx) in timeSeriesNormalised"
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

        <p class="analytics-footer">
          {{ $t('analytics.footer', { date: lastFetchedLabel }) }}
        </p>
      </template>
    </main>
  </div>
</template>

<script setup>
/**
 * /admin/analytics — tableau de bord interne ops (US-065).
 *
 * Audience : Amine + ops Bassira. Lecture en 30 secondes :
 *   - KPI row (4 chiffres bruts) — total / completed / 30d / quotes
 *   - Funnel (4 étapes : visits ? → simulations → completed → quotes)
 *   - Top packages (bar chart CSS, top 5 par template_id)
 *   - Time series 30 jours (bar chart CSS quotidien des completions)
 *
 * Auth :
 *   - bassira_admin_token attendu en sessionStorage
 *   - Si absent → on remplace toute la page par un form de saisie.
 *     Pas de redirect : c'est une vue ops, l'opérateur attendu sait
 *     pourquoi il est là, et un redirect /admin/analytics → /admin/analytics
 *     créerait une boucle si le navigateur ne supporte pas sessionStorage.
 *
 * Réseau : un seul appel GET /api/admin/analytics. L'intercepteur
 * axios attache automatiquement Authorization: Bearer <token> pour
 * toute URL contenant '/admin' (cf api/index.js mis à jour pour
 * cette US).
 */
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api/index.js'
import { formatApiError } from '../utils/error-handler'

const { t } = useI18n()

// ─── Auth state ────────────────────────────────────────────────────────────
const TOKEN_KEY = 'bassira_admin_token'
const authed = ref(Boolean(sessionStorage.getItem(TOKEN_KEY)))
const tokenInput = ref('')
const gateError = ref('')

// ─── Data state ────────────────────────────────────────────────────────────
const data = ref(null)
const loading = ref(false)
const error = ref('')
const lastFetchedAt = ref(null)

// ─── Auth flow ─────────────────────────────────────────────────────────────
const login = async () => {
  const tok = (tokenInput.value || '').trim()
  if (!tok) {
    gateError.value = t('analytics.gate.errors.empty')
    return
  }
  // On stocke d'abord, puis on tente un fetch. Si 401/503 retournent on
  // vide le storage et on affiche l'erreur dans la modal.
  sessionStorage.setItem(TOKEN_KEY, tok)
  authed.value = true
  gateError.value = ''
  await fetchData(true)
  if (!data.value) {
    // fetchData a échoué — on reste authed=false pour que le form revienne.
    sessionStorage.removeItem(TOKEN_KEY)
    authed.value = false
  } else {
    tokenInput.value = ''
  }
}

const logout = () => {
  sessionStorage.removeItem(TOKEN_KEY)
  authed.value = false
  data.value = null
  error.value = ''
}

// ─── API ───────────────────────────────────────────────────────────────────
const fetchData = async (silent = false) => {
  loading.value = true
  if (!silent) error.value = ''
  try {
    const res = await api.get('/api/admin/analytics')
    // L'intercepteur unwrap déjà le wrapper Flask. Quand il ne le fait
    // pas (cas d'edge avec axios 1.x) on lit res.data en backup.
    const payload = res && res.data !== undefined ? res.data : res
    data.value = payload
    lastFetchedAt.value = new Date()
  } catch (err) {
    error.value = formatApiError(err) || t('analytics.error.generic')
    if (silent) {
      // Le form de gate gère son propre message — on ne pollue pas
      // l'écran principal avant que l'utilisateur ait validé un token.
      gateError.value = error.value
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (authed.value) fetchData()
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
  transition: background 0.18s ease, transform 0.18s ease;
}
.analytics-gate-submit:hover {
  background: var(--ms-orange-strong);
  transform: translateY(-1px);
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

/* ── RTL support ─────────────────────────────────────────────────────────── */
[dir="rtl"] .analytics-back-arrow { transform: scaleX(-1); }
[dir="rtl"] .analytics-funnel-fill,
[dir="rtl"] .analytics-top-fill {
  background: linear-gradient(270deg, var(--ms-orange) 0%, rgba(255, 133, 81, 0.55) 100%);
}
</style>
