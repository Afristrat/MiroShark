<template>
  <router-view />
  <ThemeSwitcher />
  <button
    type="button"
    class="restart-tour-btn"
    :title="restartLabel"
    :aria-label="restartLabel"
    @click="restartTour"
  >
    <span aria-hidden="true">▶</span>
  </button>
  <LanguageSwitcher class="lang-switcher--floating" />
  <DebugPanel />
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import DebugPanel from './components/DebugPanel.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import ThemeSwitcher from './components/ThemeSwitcher.vue'

const router = useRouter()
const route = useRoute()
const { locale } = useI18n()

const restartLabel = computed(() => {
  const labels = {
    fr: 'Relancer la visite guidée',
    en: 'Restart guided tour',
    ar: 'إعادة تشغيل الجولة الإرشادية',
  }
  return labels[locale.value] || labels.fr
})

// Bouton "Relancer le tour" : ouvre l'OnboardingTour quel que soit la
// page actuelle. Si on n'est pas sur "/", on y navigue d'abord (le tour
// est instancié dans Home.vue), puis on déclenche l'évènement global.
const restartTour = async () => {
  if (route.path !== '/') {
    await router.push('/')
  }
  // Laisser le temps à Home.vue + OnboardingTour de monter avant de fire
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('bassira:reopen-tour'))
  }, 120)
}
</script>

<style>
/* ═══════════════════════════════════════════════════════════
   BASSIRA DESIGN SYSTEM — Hyperstitions v2.0
   Evangelion-inspired. Orange + Green bicolor. 1.4x scale.
   ═══════════════════════════════════════════════════════════ */

:root {
  /* ── Primary Colors ── */
  --color-orange: var(--lo);
  --color-green: var(--ls);
  --color-white: var(--lp);
  --color-black: var(--li);
  --color-gray: var(--lp2);
  --color-amber: var(--ms-peach);
  --color-red: var(--ld);

  /* ── Semantic ── */
  --background: var(--lp);
  --foreground: var(--li);

  /* ── 1.4x Modular Spacing Scale ── */
  --space-xs: 6px;
  --space-sm: 11px;
  --space-md: 22px;
  --space-lg: 34px;
  --space-xl: 56px;
  --space-2xl: 84px;

  /* ── Borders ── */
  --border-light: 2px solid rgba(10,10,10,0.08);
  --border-medium: 2px solid rgba(10,10,10,0.12);
  --border-orange: 3px solid var(--color-orange);
  --border-green: 3px solid var(--color-green);

  /* ── Transitions ── */
  --transition-fast: all 0.1s ease;
  --transition-medium: all 0.2s ease;

  /* ── Fonts ── */
  --font-display: 'Young Serif', Georgia, serif;
  --font-mono: 'Space Mono', 'Courier New', monospace;
}

/* ── Reset ── */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body, #app {
  font-family: var(--font-display);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--foreground);
  background-color: var(--background);
  transition: background-color 200ms ease, color 200ms ease;
}

/* ── Text Selection ── */
::selection {
  background: var(--color-orange);
  color: var(--color-white);
}

::-moz-selection {
  background: var(--color-orange);
  color: var(--color-white);
}

/* ── Scrollbar (1.4x scale) ── */
::-webkit-scrollbar {
  width: 11px;
  height: 11px;
}

::-webkit-scrollbar-track {
  background: var(--color-gray);
}

::-webkit-scrollbar-thumb {
  background: rgba(10,10,10,0.2);
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(10,10,10,0.3);
}

/* ── Global Button Base ── */
button {
  font-family: var(--font-mono);
  cursor: pointer;
}

/* ── Text Opacity Scale ── */
.text-primary-100 { color: rgba(10,10,10,1); }
.text-primary-70 { color: rgba(10,10,10,0.7); }
.text-primary-50 { color: rgba(10,10,10,0.5); }
.text-primary-40 { color: rgba(10,10,10,0.4); }
.text-primary-35 { color: rgba(10,10,10,0.35); }

/* ── Warning Stripes Divider ── */
.warning-stripes {
  height: 7px;
  background: repeating-linear-gradient(
    -45deg,
    var(--color-orange),
    var(--color-orange) 11px,
    var(--color-white) 11px,
    var(--color-white) 22px
  );
}

/* ── Background Grid ── */
.bg-grid {
  background-image:
    linear-gradient(rgba(67,193,101,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(67,193,101,0.04) 1px, transparent 1px);
  background-size: 70px 70px;
}

/* ── Animations ── */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes shimmer {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

@keyframes pulse-border {
  0%, 100% { border-color: var(--color-orange); }
  50% { border-color: var(--color-green); }
}

@keyframes scan {
  0%, 100% { transform: translateY(-50px); opacity: 0; }
  10% { opacity: 0.6; }
  50% { transform: translateY(50px); opacity: 0.6; }
  90% { opacity: 0.6; }
}

.animate-fade-in { animation: fade-in 0.5s ease-out; }
.animate-shimmer { animation: shimmer 2s ease-in-out infinite; }
.animate-pulse-border { animation: pulse-border 2s ease-in-out infinite; }

/* Floating LanguageSwitcher — visible on every route, RTL-flipped.
   Le composant LanguageSwitcher pose `.lang-switcher { position: relative }`
   en <style scoped> avec un attribut `[data-v-*]` (spécificité 0,1,1).
   Pour battre cette spécificité SANS `!important` (US-016), on compose ici
   avec `body` → 0,1,1 + ordre dans le head ; les blocs non-scoped sont
   injectés après les blocs scoped au runtime, donc le nôtre l'emporte.

   Top: 12px (plus proche du bord pour visibilité maximale top-of-page).
   z-index utilise --ms-z-floating-lang (1500) pour passer au-dessus de tous
   les overlays Bassira (modals, panels, dropdowns à ~1000-1200) — le
   switcher doit rester accessible même quand un modal est ouvert. */
body .lang-switcher--floating {
  position: fixed;
  top: 12px;
  inset-inline-end: 12px;
  z-index: var(--ms-z-floating-lang);
  /* Animation d'apparition discrète à l'arrivée sur la page */
  animation: lang-switcher-fadein 600ms var(--ms-ease, cubic-bezier(0.4, 0, 0.2, 1)) both;
}

@keyframes lang-switcher-fadein {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .lang-switcher--floating {
    animation: none;
  }
}

/* ── Bouton "Relancer la visite guidée" — flottant top-right, à côté du
   sélecteur de langue. Visible sur toutes les routes. */
.restart-tour-btn {
  position: fixed;
  top: 12px;
  inset-inline-end: 116px; /* à gauche du LanguageSwitcher (qui fait ~85px + 12px de marge) */
  z-index: var(--ms-z-floating-lang);
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--wi-surface, #FAF7F2);
  color: var(--wi-primary, #FF8551);
  border: 1px solid var(--wi-border, rgba(36, 25, 21, 0.12));
  border-radius: 10px;
  font-size: 14px;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: var(--transition-fast, all 0.15s ease);
  animation: lang-switcher-fadein 600ms var(--ms-ease, cubic-bezier(0.4, 0, 0.2, 1)) both;
}

.restart-tour-btn:hover {
  background: var(--wi-primary, #FF8551);
  color: var(--wi-on-primary, #FFFFFF);
  border-color: var(--wi-primary, #FF8551);
  transform: translateY(-1px);
}

.restart-tour-btn:focus-visible {
  outline: 2px solid var(--wi-primary, #FF8551);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .restart-tour-btn { animation: none; }
  .restart-tour-btn:hover { transform: none; }
}
</style>
