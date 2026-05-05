<template>
  <div class="ai-page">
    <header class="ai-topbar">
      <router-link to="/" class="ai-back" :title="$t('nav.homeTitle') || 'Accueil'">
        <span class="ai-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') || 'Bassira' }}</span>
      </router-link>
      <div class="ai-topbar-right">
        <router-link
          to="/client/dashboard"
          class="ai-pill ai-pill--ghost"
        >{{ $t('adminInvitations.backToDashboard') || 'Mon espace' }}</router-link>
      </div>
    </header>

    <main class="ai-main">
      <section class="ai-hero">
        <h1 class="ai-headline">{{ $t('adminInvitations.title') || 'Invitations' }}</h1>
        <p class="ai-sub">
          {{ $t('adminInvitations.subtitle') ||
            'Invitez les membres de votre équipe à rejoindre votre organisation Bassira. Les liens magiques expirent au bout de 7 jours.' }}
        </p>
      </section>

      <!-- Form de création -->
      <section class="ai-form-card">
        <h2 class="ai-card-title">
          {{ $t('adminInvitations.form.title') || 'Nouvelle invitation' }}
        </h2>
        <form class="ai-form" @submit.prevent="submitInvite">
          <div class="ai-field">
            <label for="invite-email">{{ $t('adminInvitations.form.email') || 'Email' }}</label>
            <input
              id="invite-email"
              v-model.trim="form.email"
              type="email"
              required
              autocomplete="email"
              :placeholder="$t('adminInvitations.form.emailPlaceholder') || 'analyste@example.com'"
            />
          </div>
          <div class="ai-field">
            <label for="invite-role">{{ $t('adminInvitations.form.role') || 'Rôle' }}</label>
            <select id="invite-role" v-model="form.role">
              <option value="member">{{ $t('adminInvitations.role.member') || 'Membre' }}</option>
              <option value="admin">{{ $t('adminInvitations.role.admin') || 'Administrateur' }}</option>
              <option value="viewer">{{ $t('adminInvitations.role.viewer') || 'Lecteur' }}</option>
            </select>
          </div>
          <button type="submit" class="ai-cta" :disabled="busy">
            {{ busy
              ? ($t('adminInvitations.form.sending') || 'Envoi…')
              : ($t('adminInvitations.form.submit') || 'Envoyer l\'invitation') }}
          </button>
        </form>
        <p v-if="formError" class="ai-error" role="alert">{{ formError }}</p>
        <p v-if="formSuccess" class="ai-success" role="status">{{ formSuccess }}</p>
      </section>

      <!-- Liste pending -->
      <section class="ai-list-card">
        <h2 class="ai-card-title">
          {{ $t('adminInvitations.list.title') || 'Invitations en attente' }}
        </h2>
        <p v-if="loading" class="ai-loading">{{ $t('adminInvitations.loading') || 'Chargement…' }}</p>
        <p v-else-if="loadError" class="ai-error" role="alert">{{ loadError }}</p>
        <p v-else-if="invitations.length === 0" class="ai-empty">
          {{ $t('adminInvitations.list.empty') || 'Aucune invitation en attente.' }}
        </p>
        <ul v-else class="ai-table">
          <li v-for="inv in invitations" :key="inv.token" class="ai-row">
            <div class="ai-row-main">
              <span class="ai-email">{{ inv.email }}</span>
              <span class="ai-role-pill" :class="`ai-role-pill--${inv.role}`">
                {{ $t(`adminInvitations.role.${inv.role}`) || inv.role }}
              </span>
            </div>
            <div class="ai-row-meta">
              <span>{{ $t('adminInvitations.list.expires') || 'Expire' }} : {{ formatDate(inv.expires_at) }}</span>
            </div>
            <div class="ai-row-actions">
              <button
                type="button"
                class="ai-action ai-action--danger"
                :disabled="revoking === inv.token"
                @click="revoke(inv)"
              >
                {{ revoking === inv.token
                  ? ($t('adminInvitations.list.revoking') || 'Révocation…')
                  : ($t('adminInvitations.list.revoke') || 'Révoquer') }}
              </button>
            </div>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  fetchAdminInvitations,
  createAdminInvitation,
  revokeAdminInvitation,
} from '../api/client'

const authStore = useAuthStore()

const form = reactive({
  email: '',
  role: 'member',
})
const busy = ref(false)
const formError = ref('')
const formSuccess = ref('')

const invitations = ref([])
const loading = ref(false)
const loadError = ref('')
const revoking = ref('')

const currentOrgId = computed(
  () => authStore.currentOrg?.id || authStore.orgs?.[0]?.id || null
)

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString(authStore.locale || 'fr', {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

async function loadInvitations() {
  loading.value = true
  loadError.value = ''
  try {
    const params = currentOrgId.value ? { org_id: currentOrgId.value } : {}
    const res = await fetchAdminInvitations(params)
    invitations.value = res?.data?.invitations || []
  } catch (err) {
    const code = err?.response?.data?.error_code
    if (code === 'INSUFFICIENT_ROLE') {
      loadError.value =
        'Vous devez être administrateur ou propriétaire de l\'organisation pour gérer les invitations.'
    } else {
      loadError.value =
        err?.response?.data?.error || err?.message || 'Erreur de chargement.'
    }
  } finally {
    loading.value = false
  }
}

async function submitInvite() {
  busy.value = true
  formError.value = ''
  formSuccess.value = ''
  try {
    const payload = {
      email: form.email,
      role: form.role,
    }
    if (currentOrgId.value) payload.org_id = currentOrgId.value
    const res = await createAdminInvitation(payload)
    if (res?.data?.invitation) {
      formSuccess.value =
        (res.data.email_sent
          ? 'Invitation envoyée à '
          : 'Invitation créée (mais l\'email n\'a pas pu être envoyé) : ')
        + res.data.invitation.email
      form.email = ''
      form.role = 'member'
      await loadInvitations()
    }
  } catch (err) {
    formError.value =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur lors de l\'envoi de l\'invitation.'
  } finally {
    busy.value = false
  }
}

async function revoke(inv) {
  revoking.value = inv.token
  try {
    await revokeAdminInvitation(inv.token)
    invitations.value = invitations.value.filter((i) => i.token !== inv.token)
  } catch (err) {
    loadError.value =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur lors de la révocation.'
  } finally {
    revoking.value = ''
  }
}

onMounted(() => {
  loadInvitations()
})
</script>

<style scoped>
.ai-page {
  min-height: 100vh;
  background: var(--ms-bg-canvas, #FAF7F2);
  color: var(--ms-text, #241915);
  font-family: 'Outfit', 'Manrope', system-ui, sans-serif;
}

.ai-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-block-end: 1px solid rgba(36, 25, 21, 0.08);
}

.ai-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ms-text, #241915);
  font-weight: 600;
}
.ai-back-arrow {
  font-size: 18px;
}

.ai-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 133, 81, 0.10);
  color: #a13f0f;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}
.ai-pill--ghost {
  background: transparent;
  border: 1px solid rgba(36, 25, 21, 0.16);
  color: var(--ms-text, #241915);
}

.ai-main {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

.ai-hero {
  margin-block-end: 32px;
}
.ai-headline {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 8px 0;
}
.ai-sub {
  font-size: 15px;
  color: #57423a;
  margin: 0;
  max-width: 640px;
}

.ai-form-card,
.ai-list-card {
  background: #ffffff;
  border: 1px solid rgba(36, 25, 21, 0.08);
  border-radius: 16px;
  padding: 24px;
  margin-block-end: 24px;
}

.ai-card-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px 0;
}

.ai-form {
  display: grid;
  grid-template-columns: 1fr 200px auto;
  gap: 12px;
  align-items: end;
}
@media (max-width: 720px) {
  .ai-form { grid-template-columns: 1fr; }
}

.ai-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-field label {
  font-size: 13px;
  font-weight: 600;
  color: #57423a;
}
.ai-field input,
.ai-field select {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  font-size: 14px;
  font-family: inherit;
}
.ai-field input:focus,
.ai-field select:focus {
  outline: 2px solid #FF8551;
  outline-offset: 1px;
}

.ai-cta {
  padding: 11px 18px;
  border-radius: 10px;
  background: #FF8551;
  color: #ffffff;
  border: none;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  font-size: 14px;
}
.ai-cta:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-error {
  margin-top: 12px;
  color: #b04220;
  font-size: 14px;
}
.ai-success {
  margin-top: 12px;
  color: #1f7a3f;
  font-size: 14px;
}

.ai-loading,
.ai-empty {
  font-size: 14px;
  color: #57423a;
  margin: 0;
}

.ai-table {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ai-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(250, 247, 242, 0.6);
  border: 1px solid rgba(36, 25, 21, 0.06);
}
@media (max-width: 720px) {
  .ai-row { grid-template-columns: 1fr; }
}

.ai-row-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ai-email {
  font-weight: 600;
  font-size: 14px;
}
.ai-role-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
  background: rgba(36, 25, 21, 0.06);
  color: #3a2e29;
}
.ai-role-pill--admin {
  background: rgba(255, 133, 81, 0.16);
  color: #a13f0f;
}
.ai-role-pill--viewer {
  background: rgba(36, 25, 21, 0.04);
  color: #57423a;
}

.ai-row-meta {
  font-size: 12px;
  color: #57423a;
}

.ai-action {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid rgba(36, 25, 21, 0.16);
  background: #ffffff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.ai-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ai-action--danger {
  color: #b04220;
  border-color: rgba(176, 66, 32, 0.30);
}
.ai-action--danger:hover:not(:disabled) {
  background: rgba(176, 66, 32, 0.06);
}
</style>
