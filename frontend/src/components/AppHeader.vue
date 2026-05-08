<template>
  <!-- ═══════════════════════════════════════════════════════════
       US-094 — AppHeader partagé sur toutes les routes
       Extrait des nav inlined de Home.vue (.navbar) et
       LandingView.vue (.lp-topbar). Inclus globalement via
       App.vue avant <router-view />.
       Tokens : --wi-* (Warm Intelligence) exclusifs.
       RTL : CSS logical properties (inset-inline-*, padding-inline-*).
       ═══════════════════════════════════════════════════════════ -->
  <header class="app-header" role="banner">
    <nav class="app-header__nav" :aria-label="$t('nav.brand')">
      <router-link to="/" class="app-header__brand" :title="$t('nav.homeTitle')">
        {{ $t('nav.brand') }}
      </router-link>

      <div class="app-header__links">
        <router-link to="/" class="app-header__link" :title="$t('nav.homeTitle')">
          {{ $t('nav.home') }}
        </router-link>
        <router-link
          to="/models"
          class="app-header__link app-header__link--featured"
          :title="$t('nav.modelsTitle')"
        >
          {{ $t('nav.models') }}
        </router-link>
        <router-link to="/calibration" class="app-header__link" :title="$t('nav.calibrationTitle')">
          {{ $t('nav.calibration') }}
        </router-link>
        <router-link to="/offres" class="app-header__link" :title="$t('nav.offersTitle')">
          {{ $t('nav.offers') }}
        </router-link>
        <router-link to="/partenaires" class="app-header__link" :title="$t('nav.partnersTitle')">
          {{ $t('nav.partners') }}
        </router-link>
        <router-link to="/devis" class="app-header__link" :title="$t('nav.contactTitle')">
          {{ $t('nav.contact') }}
        </router-link>
      </div>

      <div class="app-header__actions">
        <!-- US-138 — Sous-menu Admin unique qui regroupe Console, + Lancer
             simulation, Devis, Analytics, Branding, Users. Remplace les 3
             liens séparés (Admin/Devis/+Lancer) qui ne couvraient pas
             /admin/branding ni /admin/users. Visible super-admin uniquement.
             Le « + Lancer simulation » pointe vers /console (entry point
             réel — l'ancien /process/new ne déclenchait pas le flow). -->
        <div
          v-if="isAuthenticated && isSuperAdmin"
          ref="adminMenuRef"
          class="app-header__admin-group"
        >
          <button
            type="button"
            class="app-header__link app-header__link--auth app-header__link--admin app-header__admin-toggle"
            :title="$t('nav.adminTitle')"
            :aria-label="$t('nav.adminMenuLabel')"
            :aria-expanded="showAdminMenu"
            aria-haspopup="menu"
            @click.stop="toggleAdminMenu"
          >
            {{ $t('nav.admin') }}
            <span class="app-header__admin-caret" aria-hidden="true">▾</span>
          </button>
          <div
            v-show="showAdminMenu"
            class="app-header__admin-menu"
            role="menu"
          >
            <router-link
              to="/console"
              class="app-header__admin-item app-header__admin-item--launch"
              role="menuitem"
              :title="$t('nav.launchSimulationTitle')"
              @click="closeAdminMenu"
            >
              + {{ $t('nav.launchSimulation') }}
            </router-link>
            <router-link
              to="/admin/quotes"
              class="app-header__admin-item"
              role="menuitem"
              :title="$t('nav.adminQuotesTitle')"
              @click="closeAdminMenu"
            >
              {{ $t('nav.adminQuotes') }}
            </router-link>
            <router-link
              to="/admin/analytics"
              class="app-header__admin-item"
              role="menuitem"
              :title="$t('nav.adminAnalyticsTitle')"
              @click="closeAdminMenu"
            >
              {{ $t('nav.adminAnalytics') }}
            </router-link>
            <router-link
              to="/admin/branding"
              class="app-header__admin-item"
              role="menuitem"
              :title="$t('nav.adminBrandingTitle')"
              @click="closeAdminMenu"
            >
              {{ $t('nav.adminBranding') }}
            </router-link>
            <router-link
              to="/admin/users"
              class="app-header__admin-item"
              role="menuitem"
              :title="$t('nav.adminUsersTitle')"
              @click="closeAdminMenu"
            >
              {{ $t('nav.adminUsers') }}
            </router-link>
          </div>
        </div>
        <!-- US-107 — entrée « Console » dédiée pour les org admins
             self-service NON super-admin (les super-admins l'ont via le
             menu Admin ci-dessus). -->
        <router-link
          v-if="isAuthenticated && canRunConsole && !isSuperAdmin"
          to="/console"
          class="app-header__link app-header__link--auth"
          :title="$t('nav.consoleTitle')"
        >
          {{ $t('nav.console') }}
        </router-link>
        <router-link
          v-if="!isAuthenticated"
          to="/login"
          class="app-header__link app-header__link--auth"
          :title="$t('nav.loginTitle')"
        >
          {{ $t('nav.login') }}
        </router-link>
        <router-link
          v-else
          to="/client/dashboard"
          class="app-header__link app-header__link--auth app-header__link--featured"
          :title="$t('nav.dashboardTitle')"
        >
          {{ $t('nav.dashboard') }}
        </router-link>
        <button
          type="button"
          class="app-header__icon-btn"
          :title="restartLabel"
          :aria-label="restartLabel"
          @click="restartTour"
        >
          <span aria-hidden="true">▶</span>
        </button>
        <ThemeSwitcher class="app-header__theme" />
        <LanguageSwitcher class="app-header__lang" />
      </div>
    </nav>
  </header>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ThemeSwitcher from './ThemeSwitcher.vue'

const router = useRouter()
const route = useRoute()
const { locale } = useI18n()
const authStore = useAuthStore()
const { isAuthenticated, isSuperAdmin, currentOrg } = storeToRefs(authStore)

// US-107 — visibilité de l'entrée Console (super-admin OU org self-service).
const canRunConsole = computed(() => {
  if (isSuperAdmin.value) return true
  if (!isAuthenticated.value) return false
  return Boolean(currentOrg.value?.self_service_enabled)
})

// US-138 — sous-menu super-admin unique (regroupe Console, Devis,
// Analytics, Branding, Users + entrée « + Lancer simulation »).
const showAdminMenu = ref(false)
const adminMenuRef = ref(null)
const toggleAdminMenu = () => { showAdminMenu.value = !showAdminMenu.value }
const closeAdminMenu = () => { showAdminMenu.value = false }
const onDocumentClick = (ev) => {
  if (!showAdminMenu.value) return
  const root = adminMenuRef.value
  if (root && !root.contains(ev.target)) showAdminMenu.value = false
}
const onEscape = (ev) => {
  if (ev.key === 'Escape') showAdminMenu.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onEscape)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onEscape)
})
// Si l'utilisateur navigue vers une autre route, ferme le menu.
watch(() => route.fullPath, () => { showAdminMenu.value = false })

// Libellé du bouton « Relancer la visite guidée » localisé sans dépendre
// d'une nouvelle clé i18n (étend le pattern App.vue d'origine — US-094).
const restartLabel = computed(() => {
  const labels = {
    fr: 'Relancer la visite guidée',
    en: 'Restart guided tour',
    ar: 'إعادة تشغيل الجولة الإرشادية'
  }
  return labels[locale.value] || labels.fr
})

// Bouton « Relancer le tour » : ouvre l'OnboardingTour quel que soit
// l'écran actuel. Si on n'est pas sur "/", on y navigue d'abord (le tour
// est instancié dans Home.vue), puis on déclenche l'évènement global.
const restartTour = async () => {
  if (route.path !== '/') {
    await router.push('/')
  }
  // Laisser le temps à Home.vue + OnboardingTour de monter avant de fire.
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('bassira:reopen-tour'))
  }, 120)
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   AppHeader — sticky top, palette Warm Intelligence, RTL-safe
   ═══════════════════════════════════════════════════════════ */
.app-header {
  position: sticky;
  inset-block-start: 0;
  z-index: var(--ms-z-floating-lang, 1500);
  background: color-mix(in srgb, var(--wi-surface, #ffffff) 92%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-block-end: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  /* Animation discrète à l'arrivée pour éviter un flash brutal sur load. */
  animation: app-header-fadein 480ms var(--ms-ease, cubic-bezier(0.4, 0, 0.2, 1)) both;
}

@keyframes app-header-fadein {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-header {
    animation: none;
  }
}

.app-header__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wi-space-sm, 16px);
  max-width: 1440px;
  margin-inline: auto;
  padding-block: 12px;
  padding-inline: var(--wi-space-md, 24px);
}

/* ── Brand ── */
.app-header__brand {
  font-family: var(--wi-font-heading, 'Outfit', sans-serif);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--wi-on-bg, #241915);
  text-decoration: none;
  white-space: nowrap;
  transition: color var(--ms-transition, 200ms);
}
.app-header__brand:hover {
  color: var(--wi-primary, #a13f0f);
}

/* ── Links group (centre) ── */
.app-header__links {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}
.app-header__links::-webkit-scrollbar {
  display: none;
}

.app-header__link {
  color: var(--wi-on-surface-variant, #57423a);
  text-decoration: none;
  font-family: var(--wi-font-body, 'Manrope', sans-serif);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding-block: 6px;
  padding-inline: 12px;
  border-radius: var(--wi-radius-pill, 999px);
  white-space: nowrap;
  transition:
    color var(--ms-transition, 200ms),
    background var(--ms-transition, 200ms);
}
.app-header__link:hover {
  color: var(--wi-on-bg, #241915);
  background: var(--wi-surface-container-low, rgba(255, 241, 236, 0.6));
}
.app-header__link.router-link-active {
  color: var(--wi-primary, #a13f0f);
  font-weight: 600;
}

/* US-087/US-094 — entrée « Modèles » et « Mon espace » mises en avant. */
.app-header__link--featured {
  color: var(--wi-primary, #a13f0f);
  font-weight: 600;
}
.app-header__link--featured:hover {
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
}

/* Auth link : visuellement distinct via une bordure subtile pour
   séparer la zone publique (left) de la zone client (right). */
.app-header__link--auth {
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
}
.app-header__link--auth:hover {
  border-color: var(--wi-primary, #a13f0f);
}
.app-header__link--auth.app-header__link--featured {
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
}

/* US-095 — entrée Admin (super-admin Bassira) : pastille discrète qui
   signale le pouvoir cross-tenant sans crier. */
.app-header__link--admin {
  color: var(--wi-on-bg, #241915);
  background: var(--wi-surface-container-low, rgba(255, 241, 236, 0.6));
  border-color: var(--wi-outline-variant, rgba(36, 25, 21, 0.18));
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 12px;
}
.app-header__link--admin:hover {
  background: var(--wi-primary, #a13f0f);
  color: var(--wi-on-primary, #ffffff);
  border-color: var(--wi-primary, #a13f0f);
}

/* US-099 — Bouton « + Lancer une simulation » super-admin (CTA visible). */
.app-header__link--launch {
  color: var(--wi-on-primary, #ffffff);
  background: var(--wi-primary, #a13f0f);
  border-color: var(--wi-primary, #a13f0f);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.app-header__link--launch:hover {
  background: var(--wi-on-primary-container, #6b1f00);
  color: var(--wi-on-primary, #ffffff);
  border-color: var(--wi-on-primary-container, #6b1f00);
}

/* ── Actions group (right) ── */
.app-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.app-header__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--wi-surface, #ffffff);
  color: var(--wi-primary, #a13f0f);
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  border-radius: var(--wi-radius-md, 10px);
  font-size: 13px;
  font-family: var(--ms-font-mono, 'Space Mono', monospace);
  cursor: pointer;
  transition:
    color var(--ms-transition, 200ms),
    background var(--ms-transition, 200ms),
    border-color var(--ms-transition, 200ms),
    transform var(--ms-transition, 200ms);
}
.app-header__icon-btn:hover {
  background: var(--wi-primary, #a13f0f);
  color: var(--wi-on-primary, #ffffff);
  border-color: var(--wi-primary, #a13f0f);
  transform: translateY(-1px);
}
.app-header__icon-btn:focus-visible {
  outline: 2px solid var(--wi-primary, #a13f0f);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .app-header__icon-btn {
    transition: none;
  }
  .app-header__icon-btn:hover {
    transform: none;
  }
}

/* ── Mobile responsive ── */
@media (max-width: 900px) {
  .app-header__nav {
    padding-inline: var(--wi-space-sm, 12px);
    gap: 8px;
  }
  .app-header__link {
    padding-inline: 10px;
    font-size: 13px;
  }
}

@media (max-width: 720px) {
  .app-header__brand {
    font-size: 14px;
    letter-spacing: 0.04em;
  }
  /* Sur mobile, on cache les libellés secondaires (calibration / offres /
     partenaires / contact) ; Accueil + Modèles + auth restent visibles. */
  .app-header__links {
    gap: 0;
  }
  .app-header__link {
    padding-inline: 8px;
  }
}

@media (max-width: 540px) {
  .app-header__nav {
    flex-wrap: wrap;
    padding-block: 8px;
  }
  .app-header__links {
    order: 3;
    width: 100%;
    overflow-x: auto;
    padding-block-start: 4px;
  }
}

/* ═══════════════════════════════════════════════════════════
   US-138 — Dropdown super-admin
   ═══════════════════════════════════════════════════════════ */
.app-header__admin-group {
  position: relative;
  display: inline-flex;
}

.app-header__admin-toggle {
  /* Hérite des styles `.app-header__link` ; ajoute juste un curseur
     pointer + un alignement caret. */
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 0;
  font: inherit;
  color: inherit;
}

.app-header__admin-caret {
  display: inline-block;
  font-size: 0.75em;
  transition: transform 160ms var(--ms-ease, cubic-bezier(0.4, 0, 0.2, 1));
}

.app-header__admin-toggle[aria-expanded="true"] .app-header__admin-caret {
  transform: rotate(-180deg);
}

.app-header__admin-menu {
  position: absolute;
  inset-block-start: calc(100% + 6px);
  inset-inline-end: 0;
  min-width: 220px;
  padding: 6px;
  background: var(--wi-surface, #ffffff);
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  border-radius: 12px;
  box-shadow: 0 12px 28px -8px rgba(36, 25, 21, 0.18),
              0 4px 10px -2px rgba(36, 25, 21, 0.08);
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: calc(var(--ms-z-floating-lang, 1500) + 1);
  animation: app-header-admin-menu-in 140ms var(--ms-ease, cubic-bezier(0.4, 0, 0.2, 1));
}

@keyframes app-header-admin-menu-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.app-header__admin-item {
  display: block;
  padding: 8px 12px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--wi-on-surface, #241915);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  transition: background 140ms ease, color 140ms ease;
}

.app-header__admin-item:hover,
.app-header__admin-item:focus-visible {
  background: var(--wi-secondary-soft, rgba(255, 133, 81, 0.08));
  color: var(--wi-primary, #FF8551);
  outline: none;
}

.app-header__admin-item.router-link-active,
.app-header__admin-item.router-link-exact-active {
  background: var(--wi-primary-container-soft, rgba(255, 133, 81, 0.15));
  color: var(--wi-primary, #FF8551);
  font-weight: 600;
}

.app-header__admin-item--launch {
  color: var(--wi-primary, #FF8551);
  font-weight: 600;
  border-block-end: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.08));
  margin-block-end: 2px;
  padding-block-end: 10px;
}

@media (prefers-reduced-motion: reduce) {
  .app-header__admin-menu { animation: none; }
  .app-header__admin-caret { transition: none; }
}

/* Dark mode (--data-theme="dark") : surface inversée. */
[data-theme="dark"] .app-header__admin-menu {
  background: var(--wi-surface, #1a1310);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: 0 12px 28px -8px rgba(0, 0, 0, 0.6);
}
</style>

<!--
  ───────────────────────────────────────────────────────────────
  Override (non-scoped) : repositionner ThemeSwitcher et
  LanguageSwitcher en flux normal dans le header. Les deux composants
  utilisent `position: fixed` par défaut (state US-016 / floating)
  pour être visibles partout — ici on annule ce comportement parce
  qu'ils vivent désormais à l'intérieur du header sticky.
  Spécificité : `.app-header .lang-switcher` = 0,2,0 > scoped 0,1,1.
  ───────────────────────────────────────────────────────────────
-->
<style>
.app-header .lang-switcher {
  position: relative;
  inset-block-start: auto;
  inset-inline-end: auto;
  z-index: auto;
  animation: none;
}
.app-header .theme-switcher {
  position: relative;
  inset-block-start: auto;
  inset-inline-end: auto;
  z-index: auto;
  width: 36px;
  height: 36px;
}
</style>
