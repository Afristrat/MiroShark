<template>
  <div class="au-page">
    <!-- ── Topbar ─────────────────────────────────────────────────────── -->
    <header class="au-topbar">
      <router-link to="/" class="au-back" :title="$t('nav.homeTitle') || 'Accueil'">
        <span class="au-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') || 'Bassira' }}</span>
      </router-link>
      <div class="au-topbar-right">
        <router-link to="/client/dashboard" class="au-pill au-pill--ghost">
          {{ $t('nav.dashboard') }}
        </router-link>
      </div>
    </header>

    <main class="au-main">
      <!-- ── Hero ──────────────────────────────────────────────────────── -->
      <section class="au-hero">
        <h1 class="au-headline">{{ $t('adminUsers.title') || 'Utilisateurs' }}</h1>
        <p class="au-sub">{{ $t('adminUsers.subtitle') }}</p>
      </section>

      <!-- ── Stats ─────────────────────────────────────────────────────── -->
      <section class="au-stats-row" aria-label="Statistiques utilisateurs">
        <div class="au-stat-card" :class="{ 'au-stat-card--loading': statsLoading }">
          <span class="au-stat-value">{{ stats.total_users ?? '—' }}</span>
          <span class="au-stat-label">{{ $t('adminUsers.statsTotal') }}</span>
        </div>
        <div class="au-stat-card" :class="{ 'au-stat-card--loading': statsLoading }">
          <span class="au-stat-value">{{ stats.active_7d ?? '—' }}</span>
          <span class="au-stat-label">{{ $t('adminUsers.statsActive7d') }}</span>
        </div>
        <div class="au-stat-card" :class="{ 'au-stat-card--loading': statsLoading }">
          <span class="au-stat-value">{{ stats.new_30d ?? '—' }}</span>
          <span class="au-stat-label">{{ $t('adminUsers.statsNew30d') }}</span>
        </div>
      </section>
      <p v-if="statsError" class="au-error" role="alert">{{ statsError }}</p>

      <!-- ── Filtres ───────────────────────────────────────────────────── -->
      <section class="au-filters">
        <div class="au-filter-field">
          <label for="au-org-filter" class="au-filter-label">
            {{ $t('adminUsers.filterOrg') }}
          </label>
          <select
            id="au-org-filter"
            v-model="filterOrgId"
            class="au-select"
            @change="onFilterChange"
          >
            <option value="">{{ $t('adminUsers.filterOrgAll') }}</option>
            <option
              v-for="org in orgOptions"
              :key="org.id"
              :value="org.id"
            >
              {{ org.name }}
            </option>
          </select>
        </div>

        <div class="au-filter-field au-filter-field--grow">
          <label for="au-search" class="au-filter-label">
            {{ $t('adminUsers.search') }}
          </label>
          <input
            id="au-search"
            v-model="searchValue"
            type="search"
            class="au-input"
            :placeholder="$t('adminUsers.searchPlaceholder')"
            @input="onSearchDebounced"
          />
        </div>
      </section>

      <!-- ── Tableau ───────────────────────────────────────────────────── -->
      <section class="au-table-card">
        <p v-if="loading" class="au-loading">{{ $t('adminUsers.loading') }}</p>
        <p v-else-if="loadError" class="au-error" role="alert">{{ loadError }}</p>
        <template v-else>
          <p v-if="users.length === 0" class="au-empty">{{ $t('adminUsers.empty') }}</p>
          <div v-else class="au-table-wrapper" role="region" aria-label="Liste des utilisateurs">
            <table class="au-table" aria-label="Utilisateurs">
              <thead>
                <tr>
                  <th scope="col">{{ $t('adminUsers.table.email') }}</th>
                  <th scope="col">{{ $t('adminUsers.table.orgs') }}</th>
                  <th scope="col">{{ $t('adminUsers.table.role') }}</th>
                  <th scope="col">{{ $t('adminUsers.table.createdAt') }}</th>
                  <th scope="col">{{ $t('adminUsers.table.lastSignIn') }}</th>
                  <th scope="col">{{ $t('adminUsers.table.actions') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in users" :key="user.id" class="au-row">
                  <td class="au-cell au-cell--email">
                    <span class="au-email-text">{{ user.email }}</span>
                  </td>
                  <td class="au-cell au-cell--orgs">
                    <span v-if="user.orgs && user.orgs.length > 0" class="au-org-badges">
                      <span
                        v-for="org in user.orgs"
                        :key="org.id"
                        class="au-org-badge"
                        :title="org.name"
                      >{{ org.name }}</span>
                    </span>
                    <span v-else class="au-muted">{{ $t('adminUsers.noOrg') }}</span>
                  </td>
                  <td class="au-cell">
                    <span
                      v-if="user.orgs && user.orgs.length > 0"
                      class="au-role-pill"
                      :class="`au-role-pill--${user.orgs[0]?.role}`"
                    >
                      {{ $t(`adminUsers.role.${user.orgs[0]?.role}`) || user.orgs[0]?.role }}
                    </span>
                    <span v-else class="au-muted">—</span>
                  </td>
                  <td class="au-cell au-cell--date">
                    {{ formatDate(user.created_at) }}
                  </td>
                  <td class="au-cell au-cell--date">
                    <span v-if="user.last_sign_in_at">{{ formatDate(user.last_sign_in_at) }}</span>
                    <span v-else class="au-muted">{{ $t('adminUsers.never') }}</span>
                  </td>
                  <td class="au-cell au-cell--actions">
                    <button
                      type="button"
                      class="au-action"
                      :title="$t('adminUsers.viewSimulations')"
                      @click="openSimulations(user)"
                    >
                      {{ $t('adminUsers.viewSimulations') }}
                    </button>
                    <button
                      type="button"
                      class="au-action au-action--ghost"
                      :title="$t('adminUsers.viewProfile')"
                      @click="openProfile(user)"
                    >
                      {{ $t('adminUsers.viewProfile') }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── Pagination ─────────────────────────────────────────── -->
          <div v-if="total > pageSize" class="au-pagination" role="navigation" aria-label="Pagination">
            <button
              type="button"
              class="au-page-btn"
              :disabled="currentPage === 0"
              @click="goToPage(currentPage - 1)"
            >
              {{ $t('adminUsers.pagination.previous') }}
            </button>
            <span class="au-page-info">
              {{ currentPage + 1 }} {{ $t('adminUsers.pagination.of') }} {{ totalPages }}
            </span>
            <button
              type="button"
              class="au-page-btn"
              :disabled="currentPage >= totalPages - 1"
              @click="goToPage(currentPage + 1)"
            >
              {{ $t('adminUsers.pagination.next') }}
            </button>
          </div>
        </template>
      </section>
    </main>

    <!-- ── Modal Simulations ──────────────────────────────────────────── -->
    <div
      v-if="simsModal.open"
      class="au-modal-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="$t('adminUsers.modal.simulationsTitle')"
      @click.self="closeModals"
    >
      <div class="au-modal">
        <header class="au-modal-header">
          <h2 class="au-modal-title">{{ $t('adminUsers.modal.simulationsTitle') }}</h2>
          <p class="au-modal-subtitle">{{ simsModal.user?.email }}</p>
          <button type="button" class="au-modal-close" @click="closeModals">
            {{ $t('adminUsers.modal.close') }}
          </button>
        </header>
        <div class="au-modal-body">
          <p v-if="simsModal.loading" class="au-loading">{{ $t('adminUsers.modal.loading') }}</p>
          <p v-else-if="simsModal.error" class="au-error">{{ simsModal.error }}</p>
          <p v-else-if="simsModal.sims.length === 0" class="au-empty">
            {{ $t('adminUsers.modal.empty') }}
          </p>
          <ul v-else class="au-sims-list">
            <li v-for="sim in simsModal.sims" :key="sim.simulation_id" class="au-sim-row">
              <div class="au-sim-main">
                <code class="au-sim-id">{{ sim.simulation_id }}</code>
                <span class="au-sim-org">{{ sim.org_name || sim.org_id }}</span>
              </div>
              <div class="au-sim-meta">
                <span class="au-sim-published" :class="{ 'au-sim-published--yes': sim.is_published }">
                  {{ sim.is_published
                    ? $t('adminUsers.modal.yes')
                    : $t('adminUsers.modal.no') }}
                </span>
                <span class="au-sim-date">{{ formatDate(sim.created_at) }}</span>
              </div>
              <div class="au-sim-actions">
                <router-link
                  :to="`/admin/simulations?user_id=${sim.simulation_id}`"
                  class="au-action au-action--link"
                >
                  →
                </router-link>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ── Modal Profil ───────────────────────────────────────────────── -->
    <div
      v-if="profileModal.open"
      class="au-modal-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="$t('adminUsers.modal.profileTitle')"
      @click.self="closeModals"
    >
      <div class="au-modal">
        <header class="au-modal-header">
          <h2 class="au-modal-title">{{ $t('adminUsers.modal.profileTitle') }}</h2>
          <button type="button" class="au-modal-close" @click="closeModals">
            {{ $t('adminUsers.modal.close') }}
          </button>
        </header>
        <div class="au-modal-body">
          <dl class="au-profile-dl" v-if="profileModal.user">
            <div class="au-dl-row">
              <dt>{{ $t('adminUsers.table.email') }}</dt>
              <dd>{{ profileModal.user.email }}</dd>
            </div>
            <div class="au-dl-row">
              <dt>ID</dt>
              <dd><code>{{ profileModal.user.id }}</code></dd>
            </div>
            <div class="au-dl-row">
              <dt>{{ $t('adminUsers.table.createdAt') }}</dt>
              <dd>{{ formatDate(profileModal.user.created_at) }}</dd>
            </div>
            <div class="au-dl-row">
              <dt>{{ $t('adminUsers.table.lastSignIn') }}</dt>
              <dd>
                {{ profileModal.user.last_sign_in_at
                  ? formatDate(profileModal.user.last_sign_in_at)
                  : $t('adminUsers.never') }}
              </dd>
            </div>
            <div class="au-dl-row">
              <dt>{{ $t('adminUsers.table.orgs') }}</dt>
              <dd>
                <ul v-if="profileModal.user.orgs && profileModal.user.orgs.length > 0" class="au-org-list">
                  <li
                    v-for="org in profileModal.user.orgs"
                    :key="org.id"
                    class="au-org-row"
                  >
                    <span class="au-org-badge">{{ org.name }}</span>
                    <span class="au-role-pill" :class="`au-role-pill--${org.role}`">
                      {{ $t(`adminUsers.role.${org.role}`) || org.role }}
                    </span>
                    <button
                      type="button"
                      class="au-org-remove"
                      :disabled="orgsForm.busy"
                      :title="$t('adminUsers.orgs.remove')"
                      @click="removeOrg(org.id)"
                    >
×
</button>
                  </li>
                </ul>
                <span v-else class="au-muted">{{ $t('adminUsers.noOrg') }}</span>
              </dd>
            </div>
          </dl>

          <!-- ── US-138 — Affecter / créer une organisation ──────────── -->
          <section class="au-orgs-actions" v-if="isSuperAdmin">
            <h3 class="au-orgs-title">{{ $t('adminUsers.orgs.title') }}</h3>

            <p v-if="orgsForm.error" class="au-error" role="alert">{{ orgsForm.error }}</p>
            <p v-if="orgsForm.success" class="au-success">{{ orgsForm.success }}</p>

            <div v-if="!orgsForm.creating" class="au-orgs-add">
              <select
                v-model="orgsForm.selectedOrgId"
                class="au-select"
                :disabled="orgsForm.busy"
              >
                <option value="">{{ $t('adminUsers.orgs.pickOrg') }}</option>
                <option v-for="o in availableOrgs" :key="o.id" :value="o.id">
                  {{ o.name }}{{ o.slug ? ` (${o.slug})` : '' }}
                </option>
              </select>
              <select
                v-model="orgsForm.selectedRole"
                class="au-select"
                :disabled="orgsForm.busy"
              >
                <option value="member">{{ $t('adminUsers.role.member') }}</option>
                <option value="admin">{{ $t('adminUsers.role.admin') }}</option>
                <option value="owner">{{ $t('adminUsers.role.owner') }}</option>
              </select>
              <button
                type="button"
                class="au-action"
                :disabled="orgsForm.busy || !orgsForm.selectedOrgId"
                @click="addOrg"
              >
                {{ orgsForm.busy ? '…' : $t('adminUsers.orgs.add') }}
              </button>
              <button
                type="button"
                class="au-action au-action--ghost"
                :disabled="orgsForm.busy"
                @click="toggleCreateForm(true)"
              >
                + {{ $t('adminUsers.orgs.createNew') }}
              </button>
            </div>

            <form
              v-else
              class="au-orgs-create"
              @submit.prevent="createOrgInline"
            >
              <div class="au-create-grid">
                <div class="au-filter-field">
                  <label class="au-filter-label">{{ $t('adminUsers.orgs.newName') }} *</label>
                  <input
                    v-model.trim="orgsForm.newName"
                    type="text"
                    class="au-input"
                    :placeholder="$t('adminUsers.orgs.newNamePlaceholder')"
                    required
                    maxlength="200"
                    :disabled="orgsForm.busy"
                  />
                </div>
                <div class="au-filter-field">
                  <label class="au-filter-label">{{ $t('adminUsers.orgs.newCountry') }}</label>
                  <input
                    v-model.trim="orgsForm.newCountry"
                    type="text"
                    class="au-input"
                    placeholder="MA"
                    maxlength="2"
                    :disabled="orgsForm.busy"
                  />
                </div>
                <div class="au-filter-field">
                  <label class="au-filter-label">{{ $t('adminUsers.orgs.newRole') }}</label>
                  <select
                    v-model="orgsForm.newAssignRole"
                    class="au-select"
                    :disabled="orgsForm.busy"
                  >
                    <option value="member">{{ $t('adminUsers.role.member') }}</option>
                    <option value="admin">{{ $t('adminUsers.role.admin') }}</option>
                    <option value="owner">{{ $t('adminUsers.role.owner') }}</option>
                  </select>
                </div>
              </div>
              <div class="au-create-actions">
                <button
                  type="submit"
                  class="au-action"
                  :disabled="orgsForm.busy || !orgsForm.newName"
                >
                  {{ orgsForm.busy ? '…' : $t('adminUsers.orgs.createAndAssign') }}
                </button>
                <button
                  type="button"
                  class="au-action au-action--ghost"
                  :disabled="orgsForm.busy"
                  @click="toggleCreateForm(false)"
                >
                  {{ $t('adminUsers.modal.close') }}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import {
  fetchAdminUsers,
  fetchAdminUsersStats,
  fetchAdminUserSimulations,
  addUserToOrg,
  removeUserFromOrg,
  fetchAllOrganizations,
  createOrganization,
} from '../api/client'

const authStore = useAuthStore()
const { isSuperAdmin } = storeToRefs(authStore)
const { t } = useI18n()

// ── État filtres ─────────────────────────────────────────────────────────────
const filterOrgId = ref('')
const searchValue = ref('')
let searchDebounceTimer = null

// ── État liste ───────────────────────────────────────────────────────────────
const users = ref([])
const total = ref(0)
const loading = ref(false)
const loadError = ref('')

// ── Pagination ───────────────────────────────────────────────────────────────
const pageSize = 50
const currentPage = ref(0)
const totalPages = computed(() => Math.ceil(total.value / pageSize))

// ── Stats ────────────────────────────────────────────────────────────────────
const stats = reactive({ total_users: null, active_7d: null, new_30d: null })
const statsLoading = ref(false)
const statsError = ref('')

// ── Orgs disponibles pour le filtre ─────────────────────────────────────────
const orgOptions = computed(() => {
  const seen = new Set()
  const result = []
  for (const user of users.value) {
    for (const org of (user.orgs || [])) {
      if (!seen.has(org.id)) {
        seen.add(org.id)
        result.push({ id: org.id, name: org.name })
      }
    }
  }
  return result
})

// ── Modals ───────────────────────────────────────────────────────────────────
const simsModal = reactive({
  open: false,
  user: null,
  sims: [],
  loading: false,
  error: '',
})

const profileModal = reactive({
  open: false,
  user: null,
})

// US-138 — gestion des memberships utilisateur ↔ organisation
const allOrgs = ref([])
const orgsForm = reactive({
  selectedOrgId: '',
  selectedRole: 'member',
  busy: false,
  error: '',
  success: '',
  creating: false,
  newName: '',
  newCountry: 'MA',
  newAssignRole: 'member',
})

// Orgs auxquelles l'utilisateur n'est PAS encore membre — pour le dropdown.
const availableOrgs = computed(() => {
  const userOrgIds = new Set(
    (profileModal.user?.orgs || []).map((o) => o.id)
  )
  return allOrgs.value.filter((o) => !userOrgIds.has(o.id))
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString(authStore.locale || 'fr', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

// ── Chargement ───────────────────────────────────────────────────────────────
async function loadUsers() {
  loading.value = true
  loadError.value = ''
  try {
    const params = {
      limit: pageSize,
      offset: currentPage.value * pageSize,
    }
    if (filterOrgId.value) params.org_id = filterOrgId.value
    if (searchValue.value.trim()) params.search = searchValue.value.trim()

    const res = await fetchAdminUsers(params)
    users.value = res?.data?.users || []
    total.value = res?.data?.total ?? 0
  } catch (err) {
    loadError.value =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur de chargement des utilisateurs.'
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  statsLoading.value = true
  statsError.value = ''
  try {
    const res = await fetchAdminUsersStats()
    const d = res?.data || {}
    stats.total_users = d.total_users ?? 0
    stats.active_7d = d.active_7d ?? 0
    stats.new_30d = d.new_30d ?? 0
  } catch (err) {
    statsError.value =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur de chargement des statistiques.'
  } finally {
    statsLoading.value = false
  }
}

// ── Événements filtres ───────────────────────────────────────────────────────
function onFilterChange() {
  currentPage.value = 0
  loadUsers()
}

function onSearchDebounced() {
  clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 0
    loadUsers()
  }, 350)
}

function goToPage(page) {
  currentPage.value = page
  loadUsers()
}

// ── Modal simulations ────────────────────────────────────────────────────────
async function openSimulations(user) {
  simsModal.open = true
  simsModal.user = user
  simsModal.sims = []
  simsModal.error = ''
  simsModal.loading = true
  try {
    const res = await fetchAdminUserSimulations(user.id, { limit: 20 })
    simsModal.sims = res?.data?.simulations || []
  } catch (err) {
    simsModal.error =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur de chargement des simulations.'
  } finally {
    simsModal.loading = false
  }
}

// ── Modal profil ─────────────────────────────────────────────────────────────
function openProfile(user) {
  profileModal.open = true
  profileModal.user = user
  // US-138 — reset du form orgs à chaque ouverture
  orgsForm.selectedOrgId = ''
  orgsForm.selectedRole = 'member'
  orgsForm.error = ''
  orgsForm.success = ''
  orgsForm.creating = false
  orgsForm.newName = ''
  orgsForm.newCountry = 'MA'
  orgsForm.newAssignRole = 'member'
  // Pré-charger la liste d'orgs pour les super-admins (idempotent)
  if (isSuperAdmin.value && allOrgs.value.length === 0) {
    loadAllOrgs()
  }
}

function closeModals() {
  simsModal.open = false
  profileModal.open = false
}

// ── US-138 — chargement des orgs + actions membership ───────────────────────

async function loadAllOrgs() {
  try {
    const res = await fetchAllOrganizations()
    const list = res?.data?.organizations || res?.data || []
    allOrgs.value = Array.isArray(list)
      ? list
          .map((o) => ({ id: o.id, name: o.name, slug: o.slug }))
          .filter((o) => o.id)
          .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
      : []
  } catch (err) {
    // Silencieux — la section Orgs gère l'absence (dropdown vide).
    allOrgs.value = []
  }
}

function toggleCreateForm(force) {
  orgsForm.creating = typeof force === 'boolean' ? force : !orgsForm.creating
  orgsForm.error = ''
  orgsForm.success = ''
}

function _refreshAfterMembershipChange(updatedUserOrgs) {
  // Met à jour profileModal.user.orgs ET la même ligne dans la liste users
  // pour que la fermeture/réouverture du modal reflète le bon état.
  if (profileModal.user) {
    profileModal.user.orgs = updatedUserOrgs
    const idx = users.value.findIndex((u) => u.id === profileModal.user.id)
    if (idx !== -1) {
      users.value[idx] = { ...users.value[idx], orgs: updatedUserOrgs }
    }
  }
}

async function addOrg() {
  if (!profileModal.user || !orgsForm.selectedOrgId) return
  orgsForm.busy = true
  orgsForm.error = ''
  orgsForm.success = ''
  try {
    await addUserToOrg(profileModal.user.id, orgsForm.selectedOrgId, orgsForm.selectedRole)
    // Reload de l'user pour avoir la liste à jour
    await loadUsers()
    const fresh = users.value.find((u) => u.id === profileModal.user.id)
    if (fresh) _refreshAfterMembershipChange(fresh.orgs || [])
    orgsForm.success = t('adminUsers.orgs.addedSuccess')
    orgsForm.selectedOrgId = ''
    orgsForm.selectedRole = 'member'
  } catch (err) {
    orgsForm.error = err?.response?.data?.error || err?.message || 'Erreur'
  } finally {
    orgsForm.busy = false
  }
}

async function removeOrg(orgId) {
  if (!profileModal.user || !orgId) return
  orgsForm.busy = true
  orgsForm.error = ''
  orgsForm.success = ''
  try {
    await removeUserFromOrg(profileModal.user.id, orgId)
    await loadUsers()
    const fresh = users.value.find((u) => u.id === profileModal.user.id)
    if (fresh) _refreshAfterMembershipChange(fresh.orgs || [])
    orgsForm.success = t('adminUsers.orgs.removedSuccess')
  } catch (err) {
    const code = err?.response?.data?.error_code
    if (code === 'LAST_OWNER') {
      orgsForm.error = t('adminUsers.orgs.lastOwnerError')
    } else {
      orgsForm.error = err?.response?.data?.error || err?.message || 'Erreur'
    }
  } finally {
    orgsForm.busy = false
  }
}

async function createOrgInline() {
  if (!profileModal.user || !orgsForm.newName) return
  orgsForm.busy = true
  orgsForm.error = ''
  orgsForm.success = ''
  try {
    const payload = { name: orgsForm.newName }
    if (orgsForm.newCountry) payload.country_code = orgsForm.newCountry.toUpperCase()
    const res = await createOrganization(payload)
    const newOrg = res?.data
    if (!newOrg?.id) throw new Error('Réponse de création invalide.')
    // Ajouter à la liste locale + affecter immédiatement le user
    allOrgs.value = [...allOrgs.value, { id: newOrg.id, name: newOrg.name, slug: newOrg.slug }]
      .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    await addUserToOrg(profileModal.user.id, newOrg.id, orgsForm.newAssignRole)
    await loadUsers()
    const fresh = users.value.find((u) => u.id === profileModal.user.id)
    if (fresh) _refreshAfterMembershipChange(fresh.orgs || [])
    orgsForm.success = t('adminUsers.orgs.createdSuccess', { name: newOrg.name })
    orgsForm.newName = ''
    orgsForm.creating = false
  } catch (err) {
    const code = err?.response?.data?.error_code
    if (code === 'SLUG_ALREADY_EXISTS') {
      orgsForm.error = t('adminUsers.orgs.slugExistsError')
    } else {
      orgsForm.error = err?.response?.data?.error || err?.message || 'Erreur création.'
    }
  } finally {
    orgsForm.busy = false
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────
onMounted(() => {
  loadStats()
  loadUsers()
  if (isSuperAdmin.value) {
    loadAllOrgs()
  }
})
</script>

<style scoped>
/* ── Base ────────────────────────────────────────────────────────────────── */
.au-page {
  min-height: 100vh;
  background: var(--ms-bg-canvas, #FAF7F2);
  color: var(--ms-text, #241915);
  font-family: 'Outfit', 'Manrope', system-ui, sans-serif;
}

/* ── Topbar ───────────────────────────────────────────────────────────────── */
.au-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-block-end: 1px solid rgba(36, 25, 21, 0.08);
}
.au-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ms-text, #241915);
  font-weight: 600;
}
.au-back-arrow { font-size: 18px; }

.au-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}
.au-pill--ghost {
  background: transparent;
  border: 1px solid rgba(36, 25, 21, 0.16);
  color: var(--ms-text, #241915);
}

/* ── Main ─────────────────────────────────────────────────────────────────── */
.au-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

/* ── Hero ─────────────────────────────────────────────────────────────────── */
.au-hero { margin-block-end: 28px; }
.au-headline {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
}
.au-sub {
  font-size: 15px;
  color: #57423a;
  margin: 0;
  max-width: 680px;
}

/* ── Stats ────────────────────────────────────────────────────────────────── */
.au-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-block-end: 24px;
}
@media (max-width: 600px) {
  .au-stats-row { grid-template-columns: 1fr; }
}

.au-stat-card {
  background: #ffffff;
  border: 1px solid rgba(36, 25, 21, 0.08);
  border-radius: 14px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: opacity 0.2s;
}
.au-stat-card--loading { opacity: 0.5; }

.au-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #FF8551;
  line-height: 1;
}
.au-stat-label {
  font-size: 13px;
  color: #57423a;
  font-weight: 500;
}

/* ── Filtres ──────────────────────────────────────────────────────────────── */
.au-filters {
  display: flex;
  gap: 12px;
  margin-block-end: 16px;
  flex-wrap: wrap;
}
.au-filter-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 180px;
}
.au-filter-field--grow { flex: 1; }
.au-filter-label {
  font-size: 12px;
  font-weight: 600;
  color: #57423a;
}
.au-select,
.au-input {
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  font-size: 14px;
  font-family: inherit;
  color: var(--ms-text, #241915);
}
.au-select:focus,
.au-input:focus {
  outline: 2px solid #FF8551;
  outline-offset: 1px;
}

/* ── Table card ───────────────────────────────────────────────────────────── */
.au-table-card {
  background: #ffffff;
  border: 1px solid rgba(36, 25, 21, 0.08);
  border-radius: 16px;
  overflow: hidden;
}
.au-table-wrapper { overflow-x: auto; }

.au-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.au-table thead tr {
  background: rgba(36, 25, 21, 0.03);
  border-block-end: 1px solid rgba(36, 25, 21, 0.08);
}
.au-table th {
  padding: 12px 14px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: #57423a;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.au-table tbody tr.au-row {
  border-block-end: 1px solid rgba(36, 25, 21, 0.05);
  transition: background 0.15s;
}
.au-table tbody tr.au-row:last-child { border-block-end: none; }
.au-table tbody tr.au-row:hover { background: rgba(255, 133, 81, 0.03); }

.au-cell {
  padding: 13px 14px;
  vertical-align: middle;
}
.au-cell--email .au-email-text {
  font-weight: 600;
  font-size: 13px;
}
.au-cell--date {
  font-size: 12px;
  color: #57423a;
  white-space: nowrap;
}
.au-cell--actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: nowrap;
}
.au-cell--orgs { max-width: 220px; }

/* ── Org badges ───────────────────────────────────────────────────────────── */
.au-org-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.au-org-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 133, 81, 0.10);
  color: #a13f0f;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Role pills ───────────────────────────────────────────────────────────── */
.au-role-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  background: rgba(36, 25, 21, 0.06);
  color: #3a2e29;
}
.au-role-pill--owner,
.au-role-pill--admin {
  background: rgba(255, 133, 81, 0.16);
  color: #a13f0f;
}
.au-role-pill--viewer {
  background: rgba(36, 25, 21, 0.04);
  color: #57423a;
}

/* ── Actions ──────────────────────────────────────────────────────────────── */
.au-action {
  padding: 6px 11px;
  border-radius: 7px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--ms-text, #241915);
  white-space: nowrap;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.au-action:hover:not(:disabled) {
  background: rgba(255, 133, 81, 0.08);
  border-color: rgba(255, 133, 81, 0.30);
}
.au-action:disabled { opacity: 0.5; cursor: not-allowed; }
.au-action--ghost {
  background: transparent;
  color: #57423a;
}
.au-action--link {
  border: none;
  background: transparent;
  color: #FF8551;
  font-size: 16px;
}

/* ── Pagination ───────────────────────────────────────────────────────────── */
.au-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0;
  border-block-start: 1px solid rgba(36, 25, 21, 0.06);
}
.au-page-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.au-page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.au-page-info { font-size: 13px; color: #57423a; }

/* ── États ────────────────────────────────────────────────────────────────── */
.au-loading,
.au-empty {
  font-size: 14px;
  color: #57423a;
  margin: 0;
  padding: 24px;
  text-align: center;
}
.au-error {
  margin: 12px 0;
  color: #b04220;
  font-size: 14px;
  padding: 0 24px;
}
.au-muted {
  color: #8a7067;
  font-size: 12px;
}

/* ── Modal ────────────────────────────────────────────────────────────────── */
.au-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(36, 25, 21, 0.40);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}
.au-modal {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(36, 25, 21, 0.18);
  width: 100%;
  max-width: 640px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.au-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 24px 24px 16px;
  border-block-end: 1px solid rgba(36, 25, 21, 0.08);
  gap: 12px;
  flex-wrap: wrap;
}
.au-modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}
.au-modal-subtitle {
  font-size: 13px;
  color: #57423a;
  margin: 4px 0 0;
  flex-basis: 100%;
}
.au-modal-close {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--ms-text, #241915);
  flex-shrink: 0;
}
.au-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

/* ── Sims list ────────────────────────────────────────────────────────────── */
.au-sims-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.au-sim-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 12px;
  align-items: center;
  padding: 11px 14px;
  border-radius: 10px;
  background: rgba(250, 247, 242, 0.6);
  border: 1px solid rgba(36, 25, 21, 0.06);
}
.au-sim-main { display: flex; flex-direction: column; gap: 3px; overflow: hidden; }
.au-sim-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #57423a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.au-sim-org { font-size: 12px; font-weight: 600; color: var(--ms-text, #241915); }
.au-sim-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.au-sim-date { font-size: 11px; color: #57423a; white-space: nowrap; }
.au-sim-published {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(36, 25, 21, 0.06);
  color: #57423a;
}
.au-sim-published--yes {
  background: rgba(31, 122, 63, 0.12);
  color: #1f7a3f;
}

/* ── Profil DL ────────────────────────────────────────────────────────────── */
.au-profile-dl {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.au-dl-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px;
  align-items: start;
}
.au-dl-row dt {
  font-size: 12px;
  font-weight: 700;
  color: #57423a;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.au-dl-row dd {
  font-size: 14px;
  margin: 0;
  word-break: break-all;
}
.au-dl-row dd code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: rgba(36, 25, 21, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

/* ── US-138 — gestion des memberships dans le modal profile ─────────── */
.au-org-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.au-org-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.au-org-remove {
  margin-inline-start: auto;
  background: none;
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  color: var(--wi-on-surface-variant, #57423a);
  width: 26px;
  height: 26px;
  border-radius: 999px;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
}
.au-org-remove:hover:not(:disabled) {
  background: var(--wi-error-container, #ffdad6);
  border-color: var(--wi-error, #c33);
  color: var(--wi-error, #c33);
}
.au-org-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.au-orgs-actions {
  margin-block-start: 24px;
  padding-block-start: 20px;
  border-block-start: 1px solid var(--wi-outline-variant, #dec0b6);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.au-orgs-title {
  font-family: var(--wi-font-heading, 'Outfit', system-ui);
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: var(--wi-on-surface, #241915);
}
.au-orgs-add {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.au-orgs-add .au-select { flex: 1 1 180px; min-width: 0; }
.au-success {
  font-size: 13px;
  color: var(--wi-on-tertiary-container, #006d44);
  background: var(--wi-secondary-container, rgba(0, 109, 68, 0.10));
  border-radius: var(--wi-radius-md, 8px);
  padding: 8px 12px;
  margin: 0;
}
.au-orgs-create {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--wi-surface-container-low, #fff1ec);
  padding: 14px;
  border-radius: var(--wi-radius-md, 12px);
}
.au-create-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 10px;
}
@media (max-width: 600px) {
  .au-create-grid { grid-template-columns: 1fr; }
}
.au-create-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
