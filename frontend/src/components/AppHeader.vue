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
        <!-- US-095 — entrée Admin réservée aux super-admins Bassira.
             Visibilité conditionnée par le flag store.isSuperAdmin
             (chargé via fetchSuperStatus côté backend, whitelist email). -->
        <router-link
          v-if="isAuthenticated && isSuperAdmin"
          to="/admin/analytics"
          class="app-header__link app-header__link--auth app-header__link--admin"
          :title="$t('nav.adminTitle')"
        >
          {{ $t('nav.admin') }}
        </router-link>
        <!-- US-099 — Bouton « + Lancer une simulation » réservé aux super-admins.
             Permet à Amine de lancer une sim depuis n'importe quelle page. -->
        <router-link
          v-if="isAuthenticated && isSuperAdmin"
          to="/process/new"
          class="app-header__link app-header__link--auth app-header__link--launch"
          :title="$t('nav.launchSimulationTitle')"
        >
          + {{ $t('nav.launchSimulation') }}
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
import { computed } from 'vue'
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
const { isAuthenticated, isSuperAdmin } = storeToRefs(authStore)

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
