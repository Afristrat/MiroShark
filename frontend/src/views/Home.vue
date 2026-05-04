<template>
  <div class="home-container">
    <!-- US-094 — La nav globale est désormais dans AppHeader.vue (App.vue),
         présente sur toutes les routes. Le bouton ⚙ Paramètres (admin/dev,
         config LLM) reste dans Home.vue mais à un emplacement discret pour
         ne pas polluer la nav publique : intégré au panneau console
         self-service masqué (cf. v-if showSelfServiceConsole). -->
    <SettingsPanel :open="settingsOpen" @close="settingsOpen = false" />
    <!-- Floating settings trigger — accessible via raccourci pour les admins
         qui ouvrent la home en mode dev. Caché aux visiteurs cold (opacité 0
         + pointer-events:none tant que l'utilisateur ne survole pas le bord
         bas-gauche de la viewport, cf. .home-settings-trigger). -->
    <button
      class="home-settings-trigger"
      @click="settingsOpen = true"
      :title="$t('home.nav.settingsTitle')"
      aria-label="Paramètres"
    >
      <span aria-hidden="true">⚙</span>
    </button>

    <div class="main-content">
      <!-- Upper Section: Hero Area — Stitch « Strategic Foresight » -->
      <section class="hero-section">
        <!-- Eyebrow pill : « بصيرة · Prospective stratégique » -->
        <div class="hero-eyebrow">
          <span class="hero-eyebrow-text">{{ $t('home.hero.eyebrow') }}</span>
        </div>

        <h1 class="main-title">
          <span class="gradient-text">{{ $t('home.hero.title') }}</span>
        </h1>

        <p class="hero-subtitle">{{ $t('home.hero.subtitle') }}</p>

        <!-- US-087 — CTAs orientés modèles publics + commande.
             Le self-service Step1-5 reste accessible techniquement (URLs
             directes /process, /simulation), mais on ne le promeut plus
             auprès des visiteurs cold : on les oriente vers les modèles
             publics ou la prise de contact commerciale. -->
        <div class="hero-cta-row">
          <router-link
            to="/models"
            class="hero-cta hero-cta--primary"
            :title="$t('home.heroCta.viewModelsTitle')"
          >
            <span>{{ $t('home.heroCta.viewModels') }}</span>
            <span class="hero-cta-arrow" aria-hidden="true">→</span>
          </router-link>
          <router-link
            to="/devis"
            class="hero-cta hero-cta--secondary"
            :title="$t('home.heroCta.orderAnalysisTitle')"
          >
            <span>{{ $t('home.heroCta.orderAnalysis') }}</span>
            <span class="hero-cta-arrow" aria-hidden="true">→</span>
          </router-link>
          <!-- US-107 — CTA tertiaire « Lancer une simulation » visible
               uniquement aux super-admins ou aux orgs self-service. -->
          <router-link
            v-if="canRunConsole"
            to="/console"
            class="hero-cta hero-cta--secondary"
            :title="$t('home.heroCta.runSimulationTitle')"
          >
            <span>{{ $t('home.heroCta.runSimulation') }}</span>
            <span class="hero-cta-arrow" aria-hidden="true">→</span>
          </router-link>
        </div>

        <!-- Trust strip : signaux Brier / sims / ISO -->
        <div class="hero-trust" role="list" :aria-label="$t('home.panel.systemStatus')">
          <span class="hero-trust-item hero-trust-mint" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">▲</span>
            <span>{{ $t('home.hero.trust.brier') }}</span>
          </span>
          <span class="hero-trust-sep" aria-hidden="true"></span>
          <span class="hero-trust-item hero-trust-orange" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">↗</span>
            <span>{{ $t('home.hero.trust.sims') }}</span>
          </span>
          <span class="hero-trust-sep" aria-hidden="true"></span>
          <span class="hero-trust-item hero-trust-mint" role="listitem">
            <span class="hero-trust-icon" aria-hidden="true">✓</span>
            <span>{{ $t('home.hero.trust.iso') }}</span>
          </span>
        </div>

        <!-- Punchline conservée pour Tier 2 Analyst (continuité éditoriale) -->
        <div class="hero-desc">
          <p>
            {{ $t('home.hero.descriptionPart1') }} <span class="highlight-bold">{{ $t('home.hero.brand') }}</span> {{ $t('home.hero.descriptionPart2') }} <span class="highlight-orange">{{ $t('home.hero.agents') }}</span> {{ $t('home.hero.descriptionPart3') }}
          </p>
          <p class="slogan-text">
            {{ $t('home.hero.slogan') }}<span class="blinking-cursor">_</span>
          </p>
        </div>

        <button class="scroll-down-btn" @click="scrollToBottom" :title="$t('home.hero.scrollDownTitle')">
          ↓
        </button>
      </section>

      <!-- Pivot models-first : SectorUseCases est désormais le bloc commercial
           principal de la home cold. 8 secteurs × 2 cas C-level → /models?sector=
           ou /devis?sector=&usecase=. Préserve la mécanique US-085 + relink US-087. -->
      <SectorUseCases />

      <!-- US-107 — La console upload (graines de réalité, fetch URL,
           TrendingTopics, ScenarioSuggestions, textarea prompt, bouton
           Lancer) ne vit plus sur la home. Elle a sa route privative
           /console derrière requiresAuth + requiresSelfService.
           Lien d'accès : hero CTA "Lancer une simulation" + AppHeader. -->
    </div>

    <!-- US-060 — Onboarding solo 4 étapes (premier visit uniquement) -->
    <OnboardingTour v-model="showOnboarding" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SettingsPanel from '../components/SettingsPanel.vue'
import OnboardingTour from '../components/OnboardingTour.vue'
import SectorUseCases from '../components/SectorUseCases.vue'
import { useAuthStore } from '../stores/auth'
import { storeToRefs } from 'pinia'

// US-107 — Home.vue est désormais une page produit pure :
//   - hero + CTAs
//   - SectorUseCases
//   - OnboardingTour (premier visit)
// La console upload (graines de réalité, fetch URL, TrendingTopics,
// ScenarioSuggestions, textarea, Lancer) a été extraite vers ConsoleView
// (route /console privative). Plus aucune logique d'upload sur la home.

const { t: _t } = useI18n()
const settingsOpen = ref(false)

// US-107 — visibilité du CTA tertiaire « Lancer une simulation » qui
// redirige vers /console (super-admin OU org self-service).
const authStore = useAuthStore()
const { isAuthenticated, isSuperAdmin, currentOrg } = storeToRefs(authStore)
const canRunConsole = computed(() => {
  if (isSuperAdmin.value) return true
  if (!isAuthenticated.value) return false
  return Boolean(currentOrg.value?.self_service_enabled)
})

// US-060 — Onboarding solo 4 étapes : visible uniquement au premier visit.
// Le flag `bassira_onboarding_done` est posé par OnboardingTour quand
// l'utilisateur clique Skip / Suivant final / Lancer un exemple.
const showOnboarding = ref(
  typeof window !== 'undefined' && !window.localStorage?.getItem('bassira_onboarding_done')
)

const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

// Start simulation - navigate immediately, API calls happen on the Process page
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  // Store data pending upload
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement, urlDocs.value)

    // Navigate immediately to Process page (using special identifier for new project)
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   HOME — Hyperstitions Design System applied
   ═══════════════════════════════════════════════════════════ */

.home-container {
  min-height: 100vh;
  background: var(--wi-bg);
  font-family: var(--ms-font-body);
  color: var(--wi-on-bg);
}

/* US-094 — Trigger discret pour ouvrir SettingsPanel (admin/dev only).
   Bord bas-gauche, faible opacité au repos, opacité 1 au hover/focus.
   N'apparaît PAS dans la nav publique (cf. AppHeader). */
.home-settings-trigger {
  position: fixed;
  inset-block-end: 12px;
  inset-inline-start: 12px;
  z-index: var(--ms-z-toast, 1400);
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--wi-surface, #ffffff);
  color: var(--wi-on-surface-variant, #57423a);
  border: 1px solid var(--wi-outline-variant, rgba(36, 25, 21, 0.12));
  border-radius: 50%;
  font-size: 14px;
  cursor: pointer;
  opacity: 0.25;
  transition:
    opacity var(--ms-transition, 200ms),
    color var(--ms-transition, 200ms),
    background var(--ms-transition, 200ms),
    transform var(--ms-transition, 200ms);
}
.home-settings-trigger:hover,
.home-settings-trigger:focus-visible {
  opacity: 1;
  color: var(--wi-primary, #a13f0f);
  background: var(--wi-primary-soft, rgba(161, 63, 15, 0.08));
  transform: rotate(40deg);
  outline: none;
}
.home-settings-trigger:focus-visible {
  outline: 2px solid var(--wi-primary, #a13f0f);
  outline-offset: 2px;
}

/* Anciens styles `.navbar / .nav-brand / .nav-links / .nav-link /
   .nav-link--featured / .nav-link-action / .settings-btn / .compass /
   .arrow` retirés — la nav globale vit désormais dans AppHeader.vue (US-094).
   Le bouton ⚙ (admin) est remplacé par `.home-settings-trigger` plus haut. */

/* ── Main Content ── */
.main-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--ms-space-12) var(--ms-space-6);
}

/* ── Hero Section — Stitch « Strategic Foresight » ── */
.hero-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: var(--ms-space-12);
  padding: var(--ms-space-12) var(--ms-space-6);
  position: relative;
  background: var(--wi-bg);
  border-radius: var(--wi-radius-card);
}

/* Eyebrow pill : « بصيرة · Prospective stratégique » sur fond --wi-primary-soft */
.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  padding: 6px var(--ms-space-4);
  background: var(--wi-primary-soft);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  margin-bottom: var(--ms-space-6);
}
.hero-eyebrow-text {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 600;
  color: var(--wi-primary);
  letter-spacing: 0.01em;
}

/* Conservée pour rétro-compat — masquée tant que .tag-row n'est plus rendu */
.tag-row {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  margin-bottom: var(--ms-space-4);
  font-family: var(--ms-font-mono);
  font-size: 13px;
}
.orange-tag {
  background: var(--ms-orange);
  color: var(--ms-text-on-color);
  padding: 4px var(--ms-space-2);
  font-weight: 700;
  letter-spacing: 3px;
  font-size: 11px;
  text-transform: uppercase;
  font-family: var(--ms-font-mono);
}

.main-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h1-size);
  line-height: var(--wi-h1-leading);
  font-weight: var(--wi-h1-weight);
  letter-spacing: var(--wi-h1-tracking);
  margin: 0 0 var(--ms-space-4) 0;
  max-width: 880px;
  color: var(--wi-on-bg);
}

.gradient-text {
  color: var(--wi-on-bg);
  -webkit-text-fill-color: var(--wi-on-bg);
  display: inline;
}

.hero-subtitle {
  font-family: var(--wi-font-body);
  font-size: 20px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  max-width: 640px;
  margin: 0 0 var(--ms-space-6) 0;
}

/* US-087 — Rangée de CTAs hero (primaire + secondaire) orientés modèles
   publics + commande. Empilés en colonne sur mobile (< 640 px). */
.hero-cta-row {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--ms-space-3);
  margin-bottom: var(--ms-space-6);
}

/* CTA hero — base (utilisé par primary + secondary).
   Variante primaire : terracotta plein. Variante secondaire : ghost outlined. */
.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  border-radius: var(--wi-radius-pill);
  padding: 16px 32px;
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: opacity var(--ms-transition), transform var(--ms-transition), box-shadow var(--ms-transition), background var(--ms-transition), color var(--ms-transition);
}

.hero-cta--primary {
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: 2px solid var(--wi-primary);
  box-shadow: var(--wi-shadow-md);
}
.hero-cta--primary:hover {
  opacity: 0.92;
  background: var(--wi-primary-container);
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-lg);
  transform: translateY(-1px);
}
.hero-cta--primary:active { transform: translateY(0); }

.hero-cta--secondary {
  background: transparent;
  color: var(--wi-primary);
  border: 2px solid var(--wi-outline-variant);
}
.hero-cta--secondary:hover {
  background: var(--wi-primary-soft);
  border-color: var(--wi-primary);
  color: var(--wi-on-primary-container);
  transform: translateY(-1px);
}
.hero-cta--secondary:active { transform: translateY(0); }

.hero-cta-arrow {
  font-family: sans-serif;
  font-size: 18px;
  line-height: 1;
}

/* Trust strip : Brier · simulations · ISO 27001 */
.hero-trust {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--ms-space-4);
  background: var(--wi-surface-container-highest);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-pill);
  padding: 10px var(--ms-space-6);
  margin-bottom: var(--ms-space-8);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  font-weight: 500;
}
.hero-trust-item {
  display: inline-flex;
  align-items: center;
  gap: var(--ms-space-2);
  white-space: nowrap;
}
.hero-trust-mint { color: var(--wi-secondary); }
.hero-trust-orange { color: var(--wi-primary-container); }
.hero-trust-icon {
  font-size: 14px;
  line-height: 1;
}
.hero-trust-sep {
  display: inline-block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--wi-outline-variant);
}

.hero-desc {
  font-family: var(--ms-font-display);
  font-size: 18px;
  line-height: 1.6;
  color: var(--wi-on-surface-variant);
  max-width: 640px;
  margin-bottom: var(--ms-space-8);
}

.hero-desc p { margin-bottom: var(--ms-space-4); }

.highlight-bold {
  color: var(--wi-on-bg);
  font-weight: 600;
}

.highlight-orange {
  color: var(--wi-primary-container);
  font-family: var(--ms-font-mono);
  font-size: 0.85em;
}

.highlight-code {
  background: var(--wi-surface-container);
  padding: 2px var(--ms-space-1);
  font-family: var(--ms-font-mono);
  font-size: 0.85em;
  color: var(--wi-on-bg);
}

.slogan-text {
  font-family: var(--ms-font-display);
  font-size: 22px;
  line-height: 1.5;
  color: var(--wi-on-bg);
  border-inline-start: 2px solid var(--ms-orange);
  padding-inline-start: var(--ms-space-4);
  margin-top: var(--ms-space-4);
}

.blinking-cursor {
  color: var(--ms-mint);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.scroll-down-btn {
  margin-top: var(--ms-space-4);
  width: 40px;
  height: 40px;
  border: 1px solid var(--ms-border-strong);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ms-orange);
  font-size: 1.2rem;
  border-radius: 50%;
  transition: var(--ms-transition);
}

.scroll-down-btn:hover {
  border-color: var(--ms-orange);
  background: var(--ms-orange-soft);
}

/* ── Console Intro (header « Graines de réalité ») ── */
.console-intro {
  text-align: center;
  margin: 0 auto var(--ms-space-8) auto;
  max-width: 880px;
  padding: 0 var(--ms-space-4);
}
.console-intro-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h2-size);
  font-weight: var(--wi-h2-weight);
  line-height: var(--wi-h2-leading);
  letter-spacing: var(--wi-h2-tracking);
  color: var(--wi-on-surface);
  margin: 0 0 var(--ms-space-2) 0;
}
.console-intro-subtitle {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  color: var(--wi-on-surface-variant);
  margin: 0;
}

/* ── Dashboard Section (2-column : Status & Console) ── */
.dashboard-section {
  display: flex;
  gap: var(--ms-space-8);
  padding-top: 0;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

/* ── Left Panel — carte « Statut » ── */
.left-panel {
  flex: 0.8;
  background: var(--wi-surface);
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  padding: var(--ms-space-6);
  box-shadow: var(--wi-shadow-ambient);
}

.panel-header {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  margin-bottom: var(--ms-space-4);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.status-dot {
  color: var(--wi-secondary);
  font-size: 0.8rem;
}

.section-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  line-height: var(--wi-h3-leading);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin: 0 0 var(--ms-space-2) 0;
}

.section-desc {
  color: var(--wi-on-surface-variant);
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  line-height: var(--wi-body-md-leading);
  margin-bottom: var(--ms-space-6);
}

/* ── Metric Cards (legacy — non rendues mais conservées en CSS) ── */
.metrics-row {
  display: flex;
  gap: var(--ms-space-4);
  margin-bottom: var(--ms-space-4);
}

.metric-card {
  border: 1px solid var(--ms-border);
  border-radius: var(--ms-radius-md);
  padding: var(--ms-space-4) var(--ms-space-6);
  min-width: 150px;
  transition: var(--ms-transition-fast);
}
.metric-card:hover { border-color: var(--ms-orange); }
.metric-value {
  font-family: var(--ms-font-display);
  font-size: 28px;
  margin-bottom: var(--ms-space-1);
}
.metric-label {
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--ms-text-muted);
  letter-spacing: 0.06em;
}

/* ── Workflow Steps — carte douce sans corners terminal ── */
.steps-container {
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--wi-radius-interactive);
  padding: var(--ms-space-5);
  background: var(--wi-surface-container-low);
  position: relative;
}

.steps-header {
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-on-surface-variant);
  margin-bottom: var(--ms-space-4);
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.diamond-icon {
  color: var(--wi-primary-container);
  font-size: 1rem;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-4);
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ms-space-4);
}

.step-num {
  font-family: var(--ms-font-mono);
  font-weight: 600;
  font-size: 14px;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  min-width: 28px;
}

.step-info { flex: 1; }

.step-title {
  font-family: var(--wi-font-heading);
  font-size: 18px;
  font-weight: 500;
  color: var(--wi-on-surface);
  margin-bottom: 4px;
}

.step-desc {
  font-family: var(--wi-font-body);
  font-size: 14px;
  color: var(--wi-on-surface-variant);
  line-height: 1.6;
}

/* ── Right Console — carte « Upload » Stitch ── */
.right-panel { flex: 1.2; }

.console-box {
  background: var(--wi-surface);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 4px solid var(--wi-primary-container);
  border-radius: var(--wi-radius-card);
  padding: var(--ms-space-2);
  position: relative;
  box-shadow: var(--wi-shadow-ambient);
}

.console-section { padding: var(--ms-space-4); }
.console-section.btn-section { padding-top: 0; }

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.console-label {
  font-weight: 600;
  letter-spacing: 0.12em;
}
.console-meta {
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  text-transform: none;
  letter-spacing: 0;
}

/* ── Upload Zone (drag-drop "Glissez vos documents ici") ── */
.upload-zone {
  border: 2px dashed var(--wi-outline-variant);
  border-radius: var(--ms-radius-md);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: var(--ms-transition);
  background: var(--wi-surface-container-low);
}

.upload-zone.has-files { align-items: flex-start; }

.upload-zone:hover {
  border-color: var(--wi-primary-container);
  background: var(--wi-surface);
}

.upload-zone.drag-over {
  border-color: var(--wi-secondary);
  background: var(--ms-mint-soft);
}

.upload-placeholder { text-align: center; }

.upload-icon {
  width: 48px;
  height: 48px;
  border: 1px solid var(--wi-outline-variant);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--ms-space-2);
  color: var(--wi-primary);
  font-size: 1.4rem;
  background: var(--wi-surface);
}

.upload-title {
  font-family: var(--wi-font-heading);
  font-size: var(--wi-h3-size);
  font-weight: var(--wi-h3-weight);
  color: var(--wi-on-surface);
  margin-bottom: 4px;
}

.upload-hint {
  font-family: var(--wi-font-body);
  font-size: var(--wi-body-md);
  color: var(--wi-on-surface-variant);
}

/* ── File List ── */
.file-list {
  width: 100%;
  padding: var(--ms-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-1);
}

.file-item {
  display: flex;
  align-items: center;
  background: var(--wi-surface);
  padding: var(--ms-space-1) var(--ms-space-2);
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-sm);
  font-family: var(--ms-font-mono);
  font-size: 14px;
  color: var(--wi-on-surface);
}

.file-name { flex: 1; margin: 0 var(--ms-space-2); }

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: var(--wi-on-surface-variant);
  transition: var(--ms-transition-fast);
}

.remove-btn:hover { color: var(--wi-error); }

/* ── Console Divider ── */
.console-divider {
  display: flex;
  align-items: center;
  margin: var(--ms-space-2) 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--ms-border);
}

.console-divider span {
  padding: 0 var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

/* ── Text Input ── */
.input-wrapper {
  position: relative;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-md);
  background: var(--wi-surface-container-low);
  transition: var(--ms-transition-fast);
}

.input-wrapper:focus-within {
  border-color: var(--wi-primary-container);
  box-shadow: 0 0 0 3px var(--ms-orange-soft);
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: var(--ms-space-4);
  font-family: var(--ms-font-mono);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
  color: var(--wi-on-surface);
}

.code-input::placeholder {
  color: var(--ms-text-subtle);
}

.model-badge {
  position: absolute;
  bottom: var(--ms-space-1);
  inset-inline-end: var(--ms-space-2);
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.06em;
}

/* ── Launch Button (CTA primaire warm orange) ── */
.start-engine-btn {
  width: 100%;
  background: var(--wi-primary);
  color: var(--wi-on-primary);
  border: 2px solid var(--wi-primary);
  border-radius: var(--wi-radius-pill);
  padding: 16px var(--ms-space-6);
  font-family: var(--wi-font-heading);
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.15s ease;
  letter-spacing: 0.02em;
  position: relative;
  overflow: hidden;
  box-shadow: var(--wi-shadow-md);
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--wi-primary-container);
  border-color: var(--wi-primary-container);
  color: var(--wi-on-primary-container);
  box-shadow: var(--wi-shadow-lg);
}

.start-engine-btn:active:not(:disabled) {
  opacity: 0.92;
}

.start-engine-btn:disabled {
  background: var(--ms-bg-muted);
  color: var(--ms-text-subtle);
  cursor: not-allowed;
  border-color: var(--ms-border);
  box-shadow: none;
}

/* ── URL Import Section / Just Ask ── */
.url-section {
  padding-top: 0;
}

.url-input-row {
  display: flex;
  gap: var(--ms-space-2);
}

.url-input {
  flex: 1;
  border: 1px solid var(--wi-outline-variant);
  border-radius: var(--ms-radius-sm);
  background: var(--wi-surface-container-low);
  padding: var(--ms-space-2) var(--ms-space-3);
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--wi-on-surface);
  outline: none;
  transition: var(--ms-transition-fast);
  min-width: 0;
}

.url-input:focus {
  border-color: var(--wi-primary-container);
  background: var(--wi-surface);
  box-shadow: 0 0 0 3px var(--ms-orange-soft);
}

.url-input::placeholder {
  color: var(--ms-text-subtle);
}

.url-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.url-fetch-btn {
  background: var(--wi-secondary);
  color: var(--wi-on-secondary);
  border: 1px solid var(--wi-secondary);
  border-radius: var(--ms-radius-sm);
  padding: var(--ms-space-2) var(--ms-space-3);
  font-family: var(--wi-font-heading);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: var(--ms-transition-fast);
  white-space: nowrap;
}

.url-fetch-btn:hover:not(:disabled) {
  background: var(--wi-on-secondary-container);
  border-color: var(--wi-on-secondary-container);
}

.url-fetch-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.url-error {
  margin-top: var(--ms-space-1);
  font-family: var(--ms-font-mono);
  font-size: 12px;
  color: var(--wi-error);
}

.url-doc-list {
  margin-top: var(--ms-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--ms-space-1);
}

.url-doc-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ms-space-2);
  background: var(--wi-surface);
  padding: var(--ms-space-2) var(--ms-space-3);
  border: 1px solid var(--wi-outline-variant);
  border-inline-start: 3px solid var(--wi-secondary);
  border-radius: var(--ms-radius-sm);
  cursor: pointer;
  transition: background var(--ms-transition-fast), border-inline-start-color var(--ms-transition-fast);
}
.url-doc-item:hover,
.url-doc-item:focus-visible {
  background: var(--ms-mint-soft);
  border-inline-start-color: var(--wi-primary-container);
  outline: none;
}

.url-doc-icon {
  color: var(--wi-secondary);
  font-size: 14px;
  margin-top: 1px;
  flex-shrink: 0;
}

.url-doc-info {
  flex: 1;
  min-width: 0;
}

.url-doc-title {
  font-family: var(--wi-font-heading);
  font-size: 14px;
  font-weight: 500;
  color: var(--wi-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.url-doc-meta {
  font-family: var(--ms-font-mono);
  font-size: 11px;
  color: var(--wi-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Footer (legacy — non rendu) ── */
.attribution-footer {
  text-align: center;
  padding: var(--ms-space-6) 0;
  font-family: var(--ms-font-mono);
  font-size: 13px;
  color: var(--ms-text-subtle);
  letter-spacing: 0.06em;
}

.attribution-footer a {
  color: var(--ms-text-muted);
  text-decoration: none;
}

.attribution-footer a:hover {
  color: var(--ms-orange);
}

/* ── Doc Preview Modal ── */
.doc-preview-overlay {
  position: fixed;
  inset: 0;
  background: var(--ms-bg-overlay);
  z-index: var(--ms-z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--ms-space-8);
  animation: doc-preview-fade 0.12s ease-out;
}
@keyframes doc-preview-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.doc-preview-modal {
  background: var(--wi-surface);
  width: 760px;
  max-width: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: var(--wi-radius-card);
  border: 1px solid var(--wi-outline-variant);
  box-shadow: var(--wi-shadow-lg);
  overflow: hidden;
  font-family: var(--ms-font-mono);
}
.doc-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ms-space-3);
  padding: var(--ms-space-4) var(--ms-space-5);
  background: var(--wi-on-bg);
  color: var(--wi-surface);
}
.doc-preview-title {
  display: flex;
  align-items: center;
  gap: var(--ms-space-2);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-preview-icon { color: var(--ms-mint); flex-shrink: 0; }
.doc-preview-close {
  background: none;
  border: none;
  color: var(--wi-surface-dim);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  flex-shrink: 0;
  transition: color var(--ms-transition-fast);
}
.doc-preview-close:hover { color: var(--wi-surface); }
.doc-preview-warning {
  height: 6px;
  background: var(--wi-primary-container);
}
.doc-preview-meta {
  padding: var(--ms-space-3) var(--ms-space-5);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--wi-on-surface-variant);
  border-bottom: 1px solid var(--wi-outline-variant);
  overflow-wrap: anywhere;
}
.doc-preview-meta-sep { margin: 0 6px; }
.doc-preview-url { color: var(--wi-primary); }
.doc-preview-body {
  margin: 0;
  padding: var(--ms-space-5);
  flex: 1;
  overflow-y: auto;
  font-family: var(--ms-font-mono);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--wi-on-surface);
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--wi-surface);
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .dashboard-section { flex-direction: column; }
  .main-title { font-size: 36px; }
  .hero-subtitle { font-size: 17px; }
  .hero-cta { font-size: 16px; padding: 14px 28px; }
}

@media (max-width: 640px) {
  .main-title { font-size: 32px; }
  .hero-trust { font-size: 11px; gap: var(--ms-space-2); padding: 8px var(--ms-space-3); }
  .hero-section { padding: var(--ms-space-8) var(--ms-space-3); }
}

/* ── PDF scan warning ── */
.pdf-scan-warning {
  display: flex; gap: var(--ms-space-2); align-items: flex-start;
  background: var(--ms-peach-soft);
  border: 1px solid var(--ms-peach);
  border-radius: var(--ms-radius-sm);
  padding: var(--ms-space-2) var(--ms-space-3);
  margin-top: var(--ms-space-2);
  font-size: 13px;
  color: var(--ms-text);
}
.pdf-scan-icon { font-size: 1rem; flex-shrink: 0; color: var(--ms-peach); }
.pdf-scan-body { display: flex; flex-direction: column; gap: 4px; }
.pdf-scan-files { margin: 4px 0 0 var(--ms-space-4); padding: 0; list-style: disc; }
</style>
