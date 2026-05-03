<template>
  <!-- US-094 — AppHeader partagé sur toutes les routes (Accueil, Modèles,
       Calibration, Offres, Partenaires, Contact + auth + ThemeSwitcher +
       LanguageSwitcher + bouton « Relancer la visite guidée »). -->
  <AppHeader />
  <router-view />
  <DebugPanel />
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
import DebugPanel from './components/DebugPanel.vue'
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

/* US-094 — les blocs `.lang-switcher--floating` et `.restart-tour-btn`
   ont été retirés : ces éléments vivent désormais dans AppHeader.vue,
   intégrés au header sticky global présent sur toutes les routes. */
</style>
