<template>
  <div class="ab-page">
    <header class="ab-topbar">
      <router-link to="/" class="ab-back" :title="$t('nav.homeTitle') || 'Accueil'">
        <span class="ab-back-arrow" aria-hidden="true">←</span>
        <span>{{ $t('nav.brand') || 'BASSIRA' }}</span>
      </router-link>
      <div class="ab-topbar-right">
        <router-link to="/admin/quotes" class="ab-pill ab-pill--ghost">
          {{ $t('adminQuotes.title') || 'Devis' }}
        </router-link>
        <router-link to="/client/dashboard" class="ab-pill ab-pill--ghost">
          {{ $t('nav.dashboard') || 'Mon espace' }}
        </router-link>
      </div>
    </header>

    <main class="ab-main">
      <!-- Hero -->
      <section class="ab-hero">
        <h1 class="ab-headline">
          {{ $t('adminBranding.title') || 'Branding PDF' }}
        </h1>
        <p class="ab-sub">
          {{ $t('adminBranding.subtitle') || 'Configurez le branding des rapports PDF par organisation.' }}
        </p>
      </section>

      <!-- Contrôles : org selector + bouton nouveau -->
      <!-- Bug 3 — remplacement de l'input UUID brut par un vrai <select>
           peuplé depuis /api/admin/organizations (super-admin) ou
           auth.orgs (org admin). Évite la saisie manuelle d'UUID. -->
      <section class="ab-controls">
        <div class="ab-field ab-field--inline">
          <label for="ab-org-select">{{ $t('adminBranding.org') || 'Organisation' }}</label>
          <select
            v-if="orgOptions.length > 0"
            id="ab-org-select"
            v-model="orgId"
            class="ab-input"
            :disabled="orgsLoading"
            @change="loadBrandings"
          >
            <option value="" disabled>
              {{ orgsLoading
                ? ($t('adminBranding.orgsLoading') || 'Chargement…')
                : ($t('adminBranding.selectOrg') || 'Sélectionner une organisation') }}
            </option>
            <option v-for="o in orgOptions" :key="o.id" :value="o.id">
              {{ o.name || o.slug || o.id }}<span v-if="o.slug && o.name"> · {{ o.slug }}</span>
            </option>
          </select>
          <p v-else-if="orgsLoading" class="ab-state">
            {{ $t('adminBranding.orgsLoading') || 'Chargement des organisations…' }}
          </p>
          <p v-else class="ab-state ab-state--error">
            {{ orgsError || $t('adminBranding.noOrgs') || 'Aucune organisation disponible.' }}
          </p>
        </div>
        <button type="button" class="ab-btn ab-btn--secondary" :disabled="!orgId" @click="loadBrandings">
          ↻ {{ $t('adminBranding.refresh') || 'Recharger' }}
        </button>
        <button type="button" class="ab-btn ab-btn--primary" :disabled="!orgId" @click="openCreateModal">
          + {{ $t('adminBranding.newBranding') || 'Nouveau branding' }}
        </button>
      </section>

      <!-- État chargement / erreur / vide -->
      <p v-if="loading" class="ab-state">
        {{ $t('adminBranding.loading') || 'Chargement des brandings…' }}
      </p>
      <p v-else-if="loadError" class="ab-state ab-state--error" role="alert">{{ loadError }}</p>
      <!-- Bug 3 — explication du fallback : tant qu'aucun row n'existe en DB,
           le PDF utilise les défauts de la palette Bassira (orange/vert
           institutionnel) — ce que l'utilisateur perçoit comme « hard-codé ».
           Créer un branding ici remplace ce fallback. -->
      <div v-else-if="brandings.length === 0 && orgId" class="ab-empty-card">
        <p class="ab-empty-title">
          {{ $t('adminBranding.empty') || 'Aucun branding configuré pour cette organisation.' }}
        </p>
        <p class="ab-empty-help">
          {{ $t('adminBranding.emptyHelp')
            || 'Tant qu\'aucune configuration n\'est créée, les rapports PDF utilisent la palette Bassira par défaut (orange/vert institutionnel). Cliquez sur « Nouveau branding » pour personnaliser logo, couleurs, en-têtes et disclaimer.' }}
        </p>
      </div>

      <!-- Table des brandings -->
      <section v-if="brandings.length > 0" class="ab-table-card">
        <table class="ab-table" role="grid">
          <thead>
            <tr>
              <th>{{ $t('adminBranding.table.name') || 'Nom' }}</th>
              <th>{{ $t('adminBranding.table.validFrom') || 'Actif depuis' }}</th>
              <th>{{ $t('adminBranding.table.validTo') || 'Expiré le' }}</th>
              <th>{{ $t('adminBranding.table.status') || 'Statut' }}</th>
              <th>{{ $t('adminBranding.table.actions') || 'Actions' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in brandings" :key="b.id" class="ab-row">
              <td class="ab-cell-name">{{ b.name }}</td>
              <td class="ab-cell-date">{{ formatDate(b.valid_from) }}</td>
              <td class="ab-cell-date">{{ b.valid_to ? formatDate(b.valid_to) : '—' }}</td>
              <td>
                <span
                  class="ab-status-pill"
                  :class="b.valid_to ? 'ab-status-pill--expired' : 'ab-status-pill--active'"
                >
                  {{ b.valid_to
                    ? ($t('adminBranding.expired') || 'Expiré')
                    : ($t('adminBranding.active') || 'Actif') }}
                </span>
              </td>
              <td class="ab-cell-actions">
                <button
                  type="button"
                  class="ab-action"
                  @click="openEditModal(b)"
                >
                  {{ $t('adminBranding.form.editTitle') || 'Modifier' }}
                </button>
                <button
                  type="button"
                  class="ab-action ab-action--preview"
                  @click="openPreview(b)"
                >
                  {{ $t('adminBranding.preview') || 'Aperçu' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Modal form create / edit -->
      <div
        v-if="showModal"
        class="ab-modal-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="editingBranding ? $t('adminBranding.form.editTitle') : $t('adminBranding.form.title')"
        @click.self="closeModal"
      >
        <div class="ab-modal">
          <div class="ab-modal-header">
            <h2 class="ab-modal-title">
              {{ editingBranding
                ? ($t('adminBranding.form.editTitle') || 'Modifier le branding')
                : ($t('adminBranding.form.title') || 'Nouveau branding') }}
            </h2>
            <button type="button" class="ab-modal-close" aria-label="Fermer" @click="closeModal">✕</button>
          </div>

          <div class="ab-modal-body">
            <!-- Formulaire gauche + Aperçu droite -->
            <div class="ab-modal-split">
              <!-- Formulaire -->
              <form class="ab-form" @submit.prevent="submitForm">
                <!-- Nom -->
                <div class="ab-field">
                  <label for="ab-name">{{ $t('adminBranding.form.name') || 'Nom' }} *</label>
                  <input
                    id="ab-name"
                    v-model.trim="form.name"
                    type="text"
                    required
                    :placeholder="$t('adminBranding.form.namePlaceholder') || 'Ex : Rapport Standard MENA'"
                    class="ab-input"
                  />
                </div>

                <!-- Logo URL -->
                <div class="ab-field">
                  <label for="ab-logo">{{ $t('adminBranding.form.logoUrl') || 'URL du logo' }}</label>
                  <input
                    id="ab-logo"
                    v-model.trim="form.logo_url"
                    type="url"
                    :placeholder="$t('adminBranding.form.logoUrlPlaceholder') || 'https://…'"
                    class="ab-input"
                    @input="debouncedPreview"
                  />
                </div>

                <!-- Section En-têtes / Pieds de page -->
                <fieldset class="ab-fieldset">
                  <legend class="ab-legend">
                    {{ $t('adminBranding.form.section') || 'En-têtes et pieds de page' }}
                  </legend>
                  <p class="ab-legend-help">
                    {{ $t('adminBranding.form.sectionHelp') || 'Placeholders : logo, section, page, total, report_id, client_name, date, org_name, generated_at' }}
                  </p>
                  <div class="ab-field-grid">
                    <div class="ab-field">
                      <label for="ab-hl">{{ $t('adminBranding.form.headerLeft') || 'En-tête gauche' }}</label>
                      <input id="ab-hl" v-model="form.header_left" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-hc">{{ $t('adminBranding.form.headerCenter') || 'En-tête centre' }}</label>
                      <input id="ab-hc" v-model="form.header_center" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-hr">{{ $t('adminBranding.form.headerRight') || 'En-tête droite' }}</label>
                      <input id="ab-hr" v-model="form.header_right" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-fl">{{ $t('adminBranding.form.footerLeft') || 'Pied gauche' }}</label>
                      <input id="ab-fl" v-model="form.footer_left" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-fc">{{ $t('adminBranding.form.footerCenter') || 'Pied centre' }}</label>
                      <input id="ab-fc" v-model="form.footer_center" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-fr">{{ $t('adminBranding.form.footerRight') || 'Pied droite' }}</label>
                      <input id="ab-fr" v-model="form.footer_right" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                  </div>
                </fieldset>

                <!-- Palette -->
                <fieldset class="ab-fieldset">
                  <legend class="ab-legend">{{ $t('adminBranding.form.palette') || 'Palette de couleurs' }}</legend>
                  <div class="ab-color-grid">
                    <div class="ab-color-field">
                      <label for="ab-cp">{{ $t('adminBranding.form.palettePrimary') || 'Primaire' }}</label>
                      <div class="ab-color-row">
                        <input id="ab-cp" v-model="form.palette_primary" type="color" class="ab-color-input" @input="debouncedPreview" />
                        <input v-model="form.palette_primary" type="text" class="ab-input ab-input--hex" @input="debouncedPreview" />
                      </div>
                    </div>
                    <div class="ab-color-field">
                      <label for="ab-cs">{{ $t('adminBranding.form.paletteSecondary') || 'Secondaire' }}</label>
                      <div class="ab-color-row">
                        <input id="ab-cs" v-model="form.palette_secondary" type="color" class="ab-color-input" @input="debouncedPreview" />
                        <input v-model="form.palette_secondary" type="text" class="ab-input ab-input--hex" @input="debouncedPreview" />
                      </div>
                    </div>
                    <div class="ab-color-field">
                      <label for="ab-ct">{{ $t('adminBranding.form.paletteText') || 'Texte' }}</label>
                      <div class="ab-color-row">
                        <input id="ab-ct" v-model="form.palette_text" type="color" class="ab-color-input" @input="debouncedPreview" />
                        <input v-model="form.palette_text" type="text" class="ab-input ab-input--hex" @input="debouncedPreview" />
                      </div>
                    </div>
                    <div class="ab-color-field">
                      <label for="ab-cbg">{{ $t('adminBranding.form.paletteBackground') || 'Fond' }}</label>
                      <div class="ab-color-row">
                        <input id="ab-cbg" v-model="form.palette_background" type="color" class="ab-color-input" @input="debouncedPreview" />
                        <input v-model="form.palette_background" type="text" class="ab-input ab-input--hex" @input="debouncedPreview" />
                      </div>
                    </div>
                  </div>
                </fieldset>

                <!-- Typographie -->
                <fieldset class="ab-fieldset">
                  <legend class="ab-legend">{{ $t('adminBranding.form.typography') || 'Typographie' }}</legend>
                  <div class="ab-field-grid ab-field-grid--3">
                    <div class="ab-field">
                      <label for="ab-ft">{{ $t('adminBranding.form.fontTitles') || 'Titres' }}</label>
                      <input id="ab-ft" v-model="form.font_titles" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-fb">{{ $t('adminBranding.form.fontBody') || 'Corps' }}</label>
                      <input id="ab-fb" v-model="form.font_body" type="text" class="ab-input" @input="debouncedPreview" />
                    </div>
                    <div class="ab-field">
                      <label for="ab-fm">{{ $t('adminBranding.form.fontMono') || 'Mono' }}</label>
                      <input id="ab-fm" v-model="form.font_mono" type="text" class="ab-input" />
                    </div>
                  </div>
                </fieldset>

                <!-- Disclaimer multilingue -->
                <fieldset class="ab-fieldset">
                  <legend class="ab-legend">Disclaimer</legend>
                  <div class="ab-field">
                    <label for="ab-dfr">{{ $t('adminBranding.form.disclaimerFr') || 'FR' }}</label>
                    <input id="ab-dfr" v-model="form.disclaimer_fr" type="text" class="ab-input" />
                  </div>
                  <div class="ab-field">
                    <label for="ab-den">{{ $t('adminBranding.form.disclaimerEn') || 'EN' }}</label>
                    <input id="ab-den" v-model="form.disclaimer_en" type="text" class="ab-input" />
                  </div>
                  <div class="ab-field">
                    <label for="ab-dar">{{ $t('adminBranding.form.disclaimerAr') || 'AR' }}</label>
                    <input id="ab-dar" v-model="form.disclaimer_ar" type="text" class="ab-input" dir="rtl" />
                  </div>
                </fieldset>

                <!-- Messages -->
                <p v-if="formError" class="ab-msg ab-msg--error" role="alert">{{ formError }}</p>
                <p v-if="formSuccess" class="ab-msg ab-msg--success" role="status">{{ formSuccess }}</p>

                <!-- Actions -->
                <div class="ab-form-actions">
                  <button type="button" class="ab-btn ab-btn--ghost" :disabled="saving" @click="closeModal">
                    {{ $t('adminBranding.form.cancel') || 'Annuler' }}
                  </button>
                  <button type="submit" class="ab-btn ab-btn--primary" :disabled="saving">
                    {{ saving
                      ? ($t('adminBranding.form.saving') || 'Enregistrement…')
                      : (editingBranding
                        ? ($t('adminBranding.form.submitEdit') || 'Enregistrer')
                        : ($t('adminBranding.form.submit') || 'Créer le branding')) }}
                  </button>
                </div>
              </form>

              <!-- Aperçu live -->
              <div class="ab-preview-panel">
                <div class="ab-preview-toolbar">
                  <span class="ab-preview-label">{{ $t('adminBranding.preview') || 'Aperçu' }}</span>
                  <div class="ab-lang-selector">
                    <button
                      v-for="l in ['fr', 'en', 'ar']"
                      :key="l"
                      type="button"
                      class="ab-lang-btn"
                      :class="{ 'ab-lang-btn--active': previewLang === l }"
                      @click="setPreviewLang(l)"
                    >
{{ l.toUpperCase() }}
</button>
                  </div>
                </div>

                <div class="ab-preview-frame">
                  <p v-if="previewLoading" class="ab-preview-state">
                    {{ $t('adminBranding.previewUpdating') || 'Mise à jour de l\'aperçu…' }}
                  </p>
                  <p v-else-if="previewError" class="ab-preview-state ab-preview-state--error">
                    {{ $t('adminBranding.previewError') || 'Erreur de génération de l\'aperçu.' }}
                  </p>
                  <img
                    v-else-if="previewSvgUrl"
                    :src="previewSvgUrl"
                    alt="Aperçu branding PDF"
                    class="ab-preview-img"
                    loading="lazy"
                  />
                  <div v-else class="ab-preview-placeholder">
                    <p>Remplissez le formulaire pour voir l'aperçu.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  fetchAdminBrandings,
  createAdminBranding,
  patchAdminBranding,
  previewAdminBranding,
  fetchAllOrganizations,
} from '../api/client'

const authStore = useAuthStore()

// ── État principal ──────────────────────────────────────────────────────────

const orgId = ref(authStore.currentOrg?.id || authStore.orgs?.[0]?.id || '')
const brandings = ref([])
const loading = ref(false)
const loadError = ref('')

// Bug 3 — Liste des organisations disponibles pour le sélecteur.
//   - Super-admin Bassira : toutes les orgs de la plateforme via
//     /api/admin/organizations (le backend de branding exige org_id
//     explicite pour les super-admins, cf. _resolve_org_id).
//   - Org admin/owner non super-admin : ses propres orgs depuis le store.
const orgOptions = ref([])
const orgsLoading = ref(false)
const orgsError = ref('')

async function loadOrgOptions() {
  orgsLoading.value = true
  orgsError.value = ''
  try {
    if (authStore.isSuperAdmin) {
      const res = await fetchAllOrganizations()
      const payload = res?.data || res
      orgOptions.value = Array.isArray(payload?.organizations)
        ? payload.organizations
        : []
    } else {
      orgOptions.value = (authStore.orgs || []).filter(
        (o) => o.role === 'owner' || o.role === 'admin'
      )
    }
    // Si l'orgId préchargée n'est plus dans la liste, on prend la 1ère.
    if (orgOptions.value.length > 0) {
      const stillValid = orgOptions.value.some((o) => o.id === orgId.value)
      if (!stillValid) orgId.value = orgOptions.value[0].id
    } else {
      orgId.value = ''
    }
  } catch (err) {
    orgOptions.value = []
    orgsError.value =
      err?.response?.data?.error || err?.message || 'Impossible de charger les organisations.'
  } finally {
    orgsLoading.value = false
  }
}

// ── Modal état ──────────────────────────────────────────────────────────────

const showModal = ref(false)
const editingBranding = ref(null)
const saving = ref(false)
const formError = ref('')
const formSuccess = ref('')

// ── Aperçu live ─────────────────────────────────────────────────────────────

const previewLang = ref('fr')
const previewLoading = ref(false)
const previewError = ref(false)
const previewSvgUrl = ref('')
let previewDebounceTimer = null

// ── Formulaire réactif ──────────────────────────────────────────────────────

const DEFAULT_FORM = {
  name: '',
  logo_url: '',
  header_left: '{{logo}}',
  header_center: '{{section}}',
  header_right: 'Page {{page}}/{{total}}',
  footer_left: '{{report_id}} · CONFIDENTIEL',
  footer_center: '{{generated_at}}',
  footer_right: 'bassira.ma',
  palette_primary: '#FF8551',
  palette_secondary: '#006D44',
  palette_text: '#241915',
  palette_background: '#FAF7F2',
  font_titles: 'Outfit',
  font_body: 'Manrope',
  font_mono: 'JetBrains Mono',
  disclaimer_fr: 'Confidentiel · Probabiliste · Usage interne',
  disclaimer_en: 'Confidential · Probabilistic · Internal use',
  disclaimer_ar: 'سري · احتمالي · استخدام داخلي',
}

const form = reactive({ ...DEFAULT_FORM })

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(authStore.locale || 'fr', {
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

function _buildPayload() {
  return {
    name: form.name,
    logo_url: form.logo_url || undefined,
    header_left: form.header_left,
    header_center: form.header_center,
    header_right: form.header_right,
    footer_left: form.footer_left,
    footer_center: form.footer_center,
    footer_right: form.footer_right,
    palette_primary: form.palette_primary,
    palette_secondary: form.palette_secondary,
    palette_text: form.palette_text,
    palette_background: form.palette_background,
    font_titles: form.font_titles,
    font_body: form.font_body,
    font_mono: form.font_mono,
    disclaimer_text: {
      fr: form.disclaimer_fr,
      en: form.disclaimer_en,
      ar: form.disclaimer_ar,
    },
  }
}

// ── Chargement des brandings ─────────────────────────────────────────────────

async function loadBrandings() {
  if (!orgId.value) return
  loading.value = true
  loadError.value = ''
  try {
    const params = { org_id: orgId.value, limit: 20, offset: 0 }
    const res = await fetchAdminBrandings(params)
    brandings.value = res?.data?.data?.brandings || []
  } catch (err) {
    loadError.value =
      err?.response?.data?.error ||
      err?.message ||
      'Erreur de chargement.'
  } finally {
    loading.value = false
  }
}

// ── Modal create / edit ──────────────────────────────────────────────────────

function openCreateModal() {
  editingBranding.value = null
  Object.assign(form, { ...DEFAULT_FORM })
  formError.value = ''
  formSuccess.value = ''
  previewSvgUrl.value = ''
  previewError.value = false
  showModal.value = true
}

function openEditModal(branding) {
  editingBranding.value = branding
  const d = branding.disclaimer_text || {}
  Object.assign(form, {
    name: branding.name || '',
    logo_url: branding.logo_url || '',
    header_left: branding.header_left || DEFAULT_FORM.header_left,
    header_center: branding.header_center || DEFAULT_FORM.header_center,
    header_right: branding.header_right || DEFAULT_FORM.header_right,
    footer_left: branding.footer_left || DEFAULT_FORM.footer_left,
    footer_center: branding.footer_center || DEFAULT_FORM.footer_center,
    footer_right: branding.footer_right || DEFAULT_FORM.footer_right,
    palette_primary: branding.palette_primary || DEFAULT_FORM.palette_primary,
    palette_secondary: branding.palette_secondary || DEFAULT_FORM.palette_secondary,
    palette_text: branding.palette_text || DEFAULT_FORM.palette_text,
    palette_background: branding.palette_background || DEFAULT_FORM.palette_background,
    font_titles: branding.font_titles || DEFAULT_FORM.font_titles,
    font_body: branding.font_body || DEFAULT_FORM.font_body,
    font_mono: branding.font_mono || DEFAULT_FORM.font_mono,
    disclaimer_fr: typeof d === 'object' ? (d.fr || DEFAULT_FORM.disclaimer_fr) : DEFAULT_FORM.disclaimer_fr,
    disclaimer_en: typeof d === 'object' ? (d.en || DEFAULT_FORM.disclaimer_en) : DEFAULT_FORM.disclaimer_en,
    disclaimer_ar: typeof d === 'object' ? (d.ar || DEFAULT_FORM.disclaimer_ar) : DEFAULT_FORM.disclaimer_ar,
  })
  formError.value = ''
  formSuccess.value = ''
  previewSvgUrl.value = ''
  previewError.value = false
  showModal.value = true
  // Déclencher un aperçu initial après ouverture
  setTimeout(() => triggerPreview(), 300)
}

function closeModal() {
  showModal.value = false
  editingBranding.value = null
}

// ── Soumission du formulaire ─────────────────────────────────────────────────

async function submitForm() {
  saving.value = true
  formError.value = ''
  formSuccess.value = ''
  try {
    const payload = _buildPayload()

    if (editingBranding.value) {
      // Mise à jour : PATCH (versioning insert côté backend)
      const res = await patchAdminBranding(editingBranding.value.id, payload)
      const updated = res?.data?.data?.branding
      if (updated) {
        formSuccess.value = 'adminBranding.success.updated'
        // Rafraîchir la liste
        await loadBrandings()
        // Mettre à jour editingBranding avec la nouvelle version
        editingBranding.value = updated
      }
    } else {
      // Création : POST
      if (orgId.value) payload.org_id = orgId.value
      const res = await createAdminBranding(payload)
      const created = res?.data?.data?.branding
      if (created) {
        formSuccess.value = 'adminBranding.success.created'
        await loadBrandings()
        // Basculer en mode edit sur le nouveau branding
        editingBranding.value = created
      }
    }
  } catch (err) {
    formError.value =
      err?.response?.data?.error ||
      err?.message ||
      (editingBranding.value ? 'Erreur lors de la mise à jour.' : 'Erreur lors de la création.')
  } finally {
    saving.value = false
  }
}

// ── Aperçu live ──────────────────────────────────────────────────────────────

function openPreview(branding) {
  openEditModal(branding)
}

function setPreviewLang(lang) {
  previewLang.value = lang
  triggerPreview()
}

function debouncedPreview() {
  clearTimeout(previewDebounceTimer)
  previewDebounceTimer = setTimeout(() => {
    triggerPreview()
  }, 1000)
}

async function triggerPreview() {
  // Nécessite un branding existant en base pour appeler l'endpoint preview
  const brandingForPreview = editingBranding.value
  if (!brandingForPreview?.id) {
    // Pas encore de branding sauvegardé → pas d'aperçu via API
    previewSvgUrl.value = ''
    return
  }

  previewLoading.value = true
  previewError.value = false
  try {
    const res = await previewAdminBranding(brandingForPreview.id, previewLang.value)
    const svgB64 = res?.data?.data?.preview_svg
    if (svgB64) {
      previewSvgUrl.value = `data:image/svg+xml;base64,${svgB64}`
    }
  } catch {
    previewError.value = true
    previewSvgUrl.value = ''
  } finally {
    previewLoading.value = false
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  // Bug 3 — Si super-admin et que le flag n'est pas encore résolu, on
  // déclenche la vérification côté backend avant de décider quelle
  // source d'orgs charger (whitelist email côté serveur).
  if (authStore.isAuthenticated && !authStore.superAdminLoaded) {
    try {
      await authStore.fetchSuperStatus()
    } catch {
      /* fail-soft */
    }
  }
  await loadOrgOptions()
  if (orgId.value) {
    loadBrandings()
  }
})
</script>

<style scoped>
/* ── Page layout ────────────────────────────────────────────────────────── */
.ab-page {
  min-height: 100vh;
  background: var(--wi-bg, #fff8f6);
  color: var(--wi-on-bg, #241915);
  font-family: var(--wi-font-body, 'Manrope', system-ui, sans-serif);
}

.ab-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-block-end: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface, #ffffff);
}

.ab-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--wi-on-surface, #241915);
  font-weight: 700;
  font-family: var(--wi-font-heading, 'Outfit', system-ui, sans-serif);
}
.ab-back-arrow {
  font-size: 18px;
}

.ab-topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ab-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: var(--wi-radius-pill, 9999px);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}
.ab-pill--ghost {
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  color: var(--wi-on-surface, #241915);
}
.ab-pill--ghost:hover {
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
}

/* ── Main content ─────────────────────────────────────────────────────── */
.ab-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

.ab-hero {
  margin-block-end: 28px;
}
.ab-headline {
  font-family: var(--wi-font-heading, 'Outfit', system-ui, sans-serif);
  font-size: var(--wi-h2-size, 32px);
  font-weight: var(--wi-h2-weight, 600);
  margin: 0 0 8px 0;
  color: var(--wi-on-bg, #241915);
}
.ab-sub {
  font-size: 15px;
  color: var(--wi-on-surface-variant, #57423a);
  margin: 0;
  max-width: 640px;
}

/* ── Contrôles ────────────────────────────────────────────────────────── */
.ab-controls {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-block-end: 24px;
  flex-wrap: wrap;
}
.ab-field--inline {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ab-field--inline label {
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface-variant, #57423a);
}

/* ── États ────────────────────────────────────────────────────────────── */
.ab-state {
  font-size: 14px;
  color: var(--wi-on-surface-variant, #57423a);
  padding: 12px 0;
}
.ab-state--error {
  color: var(--wi-error, #ba1a1a);
}

/* ── Empty card (Bug 3 — état vide explicite) ──────────────────────── */
.ab-empty-card {
  background: var(--wi-surface-container-low, #fff1ec);
  border: 1px dashed var(--wi-outline-variant, #dec0b6);
  border-radius: var(--wi-radius-card, 24px);
  padding: 24px 28px;
  margin-block-end: 24px;
}
.ab-empty-title {
  font-family: var(--wi-font-heading, 'Outfit', system-ui);
  font-size: 16px;
  font-weight: 700;
  color: var(--wi-on-surface, #241915);
  margin: 0 0 8px 0;
}
.ab-empty-help {
  font-size: 13px;
  color: var(--wi-on-surface-variant, #57423a);
  line-height: 1.6;
  margin: 0;
  max-width: 720px;
}

/* ── Table ────────────────────────────────────────────────────────────── */
.ab-table-card {
  background: var(--wi-surface, #ffffff);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  border-radius: var(--wi-radius-card, 24px);
  overflow: hidden;
  margin-block-end: 24px;
}
.ab-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.ab-table thead {
  background: var(--wi-surface-container-low, #fff1ec);
}
.ab-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: var(--wi-on-surface-variant, #57423a);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.ab-row {
  border-top: 1px solid var(--wi-outline-variant, #dec0b6);
  transition: background 0.15s;
}
.ab-row:hover {
  background: var(--wi-surface-container-low, #fff1ec);
}
.ab-table td {
  padding: 12px 16px;
  vertical-align: middle;
}
.ab-cell-name {
  font-weight: 600;
}
.ab-cell-date {
  font-size: 12px;
  color: var(--wi-on-surface-variant, #57423a);
  font-family: var(--wi-font-body);
}
.ab-cell-actions {
  display: flex;
  gap: 8px;
}

/* ── Status pill ──────────────────────────────────────────────────────── */
.ab-status-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: var(--wi-radius-pill, 9999px);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.ab-status-pill--active {
  background: var(--wi-secondary-soft, rgba(0, 109, 68, 0.12));
  color: var(--wi-secondary, #006d44);
}
.ab-status-pill--expired {
  background: var(--wi-surface-container, #ffeae2);
  color: var(--wi-on-surface-variant, #57423a);
}

/* ── Boutons ──────────────────────────────────────────────────────────── */
.ab-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 18px;
  border-radius: var(--wi-radius-interactive, 12px);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s, background 0.15s;
  font-family: inherit;
}
.ab-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.ab-btn--primary {
  background: var(--wi-primary-container, #ff8551);
  color: var(--wi-on-primary, #ffffff);
}
.ab-btn--primary:hover:not(:disabled) {
  opacity: 0.9;
}
.ab-btn--secondary {
  background: var(--wi-surface, #ffffff);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  color: var(--wi-on-surface, #241915);
}
.ab-btn--ghost {
  background: transparent;
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  color: var(--wi-on-surface, #241915);
}
.ab-action {
  padding: 7px 12px;
  border-radius: var(--wi-radius-md, 8px);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface, #ffffff);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: var(--wi-on-surface, #241915);
  transition: background 0.15s;
}
.ab-action:hover {
  background: var(--wi-surface-container-low, #fff1ec);
}
.ab-action--preview {
  color: var(--wi-primary, #a13f0f);
  border-color: rgba(161, 63, 15, 0.25);
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
.ab-input {
  padding: 9px 12px;
  border-radius: var(--wi-radius-interactive, 12px);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface, #ffffff);
  font-size: 13px;
  font-family: inherit;
  color: var(--wi-on-surface, #241915);
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.ab-input:focus {
  outline: 2px solid var(--wi-primary-container, #ff8551);
  outline-offset: 1px;
  border-color: var(--wi-primary-container, #ff8551);
}
.ab-input--mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  min-width: 280px;
}
.ab-input--hex {
  width: 96px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* ── Modal ────────────────────────────────────────────────────────────── */
/* US-138 — z-index 2200 pour passer au-dessus du AppHeader sticky
   (z-index 1500 via --ms-z-floating-lang). Sans ce fix le titre + bouton
   close du modal étaient masqués par la nav (BASSIRA/Accueil/…). */
.ab-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(36, 25, 21, 0.55);
  z-index: 2200;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 32px 16px;
  overflow-y: auto;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.ab-modal {
  background: var(--wi-surface, #ffffff);
  border-radius: var(--wi-radius-card, 24px);
  width: 100%;
  max-width: 1040px;
  box-shadow: var(--wi-shadow-lg);
  overflow: hidden;
  /* US-138 v4 — grid 2 rangées (header auto + body 1fr) avec hauteur EXPLICITE
     (pas max-height). Sans hauteur explicite, 1fr résout à la hauteur intrinsèque
     des enfants — donc body=0 quand son contenu utilise height:100%. Cela
     donne à .ab-modal-body une hauteur définie à laquelle .ab-modal-split
     peut référer via height:100%. */
  display: grid;
  grid-template-rows: auto 1fr;
  height: calc(100vh - 64px);
}
.ab-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-block-end: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface-container-low, #fff1ec);
}
.ab-modal-title {
  font-family: var(--wi-font-heading, 'Outfit', system-ui);
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--wi-on-surface, #241915);
}
.ab-modal-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--wi-on-surface-variant, #57423a);
  padding: 4px 8px;
  border-radius: var(--wi-radius-sm, 4px);
  line-height: 1;
}
.ab-modal-close:hover {
  background: var(--wi-surface-container, #ffeae2);
}
.ab-modal-body {
  padding: 0;
  min-height: 0;
  overflow: hidden;       /* le scroll est délégué aux enfants (.ab-form, .ab-preview-panel) */
}

/* ── Split layout modal ───────────────────────────────────────────────── */
/* US-138 v4 — body étant la 2e rangée 1fr d'un grid avec hauteur EXPLICITE,
   sa hauteur computée est définie. Donc height:100% sur split résout
   correctement à la hauteur de body. Idem pour form/preview. */
.ab-modal-split {
  display: flex;
  height: 100%;
  min-height: 0;
}
.ab-modal-split > .ab-form {
  flex: 1 1 0;
  min-width: 0;
  height: 100%;
  max-height: 100%;
}
.ab-modal-split > .ab-preview-panel {
  flex: 0 0 340px;
  height: 100%;
  max-height: 100%;
}
@media (max-width: 860px) {
  .ab-modal-split { flex-direction: column; }
  .ab-modal-split > .ab-preview-panel { flex: 0 0 auto; }
}

/* ── Formulaire ───────────────────────────────────────────────────────── */
/* US-138 — la hauteur du form est désormais contrôlée par le parent
   flexbox (.ab-modal-body min-height:0 + height:100%) → plus de
   max-height: 80vh hardcodé qui ignorait le header sticky. */
.ab-form {
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  min-height: 0;
}
.ab-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ab-field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface-variant, #57423a);
}
.ab-fieldset {
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  border-radius: var(--wi-radius-interactive, 12px);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ab-legend {
  font-size: 12px;
  font-weight: 700;
  color: var(--wi-on-surface-variant, #57423a);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0 6px;
}
.ab-legend-help {
  font-size: 11px;
  color: var(--wi-on-surface-variant, #57423a);
  margin: 0;
  line-height: 1.5;
  font-family: 'JetBrains Mono', monospace;
  opacity: 0.8;
}
.ab-field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.ab-field-grid--3 {
  grid-template-columns: repeat(3, 1fr);
}
@media (max-width: 600px) {
  .ab-field-grid,
  .ab-field-grid--3 { grid-template-columns: 1fr; }
}
.ab-color-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.ab-color-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ab-color-field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--wi-on-surface-variant, #57423a);
}
.ab-color-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ab-color-input {
  width: 40px;
  height: 36px;
  border-radius: var(--wi-radius-md, 8px);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  padding: 2px;
  cursor: pointer;
  background: none;
}

.ab-msg {
  font-size: 13px;
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--wi-radius-md, 8px);
}
.ab-msg--error {
  background: var(--wi-error-container, #ffdad6);
  color: var(--wi-on-error-container, #93000a);
}
.ab-msg--success {
  background: var(--wi-secondary-soft, rgba(0, 109, 68, 0.12));
  color: var(--wi-secondary, #006d44);
}
.ab-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
}

/* ── Aperçu ───────────────────────────────────────────────────────────── */
.ab-preview-panel {
  border-inline-start: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface-container-low, #fff1ec);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
.ab-preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-block-end: 1px solid var(--wi-outline-variant, #dec0b6);
}
.ab-preview-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--wi-on-surface-variant, #57423a);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.ab-lang-selector {
  display: flex;
  gap: 4px;
}
.ab-lang-btn {
  padding: 4px 10px;
  border-radius: var(--wi-radius-pill, 9999px);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
  background: var(--wi-surface, #ffffff);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  color: var(--wi-on-surface-variant, #57423a);
  transition: background 0.15s;
}
.ab-lang-btn--active {
  background: var(--wi-primary-container, #ff8551);
  color: #ffffff;
  border-color: var(--wi-primary-container, #ff8551);
}
.ab-preview-frame {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow: hidden;
}
.ab-preview-state {
  font-size: 13px;
  color: var(--wi-on-surface-variant, #57423a);
  text-align: center;
}
.ab-preview-state--error {
  color: var(--wi-error, #ba1a1a);
}
.ab-preview-img {
  width: 100%;
  height: auto;
  border-radius: var(--wi-radius-md, 8px);
  box-shadow: var(--wi-shadow-md);
  border: 1px solid var(--wi-outline-variant, #dec0b6);
}
.ab-preview-placeholder {
  text-align: center;
  color: var(--wi-on-surface-variant, #57423a);
  font-size: 13px;
  opacity: 0.7;
}
</style>
