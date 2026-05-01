<template>
  <button
    type="button"
    class="theme-switcher"
    :aria-label="isDark ? t('theme.switchToLight') : t('theme.switchToDark')"
    :title="isDark ? t('theme.switchToLight') : t('theme.switchToDark')"
    @click="toggle"
  >
    <span aria-hidden="true" class="theme-switcher__icon">{{ isDark ? '☀️' : '🌙' }}</span>
  </button>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { clearChartPaletteCache } from '../utils/css-vars.js'

const { t } = useI18n()

const STORAGE_KEY = 'bassira_theme'
const isDark = ref(false)

/**
 * Applique le thème sur <html> et notifie les charts D3.
 * @param {boolean} dark
 */
function applyTheme(dark) {
  isDark.value = dark
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
  // Vider le cache de palette D3 pour forcer une relecture des tokens CSS
  clearChartPaletteCache()
  // Émettre un event global pour les charts qui écoutent sans composable
  window.dispatchEvent(new CustomEvent('theme-changed', { detail: { dark } }))
}

function toggle() {
  const newDark = !isDark.value
  localStorage.setItem(STORAGE_KEY, newDark ? 'dark' : 'light')
  applyTheme(newDark)
}

onMounted(() => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark') {
    applyTheme(true)
  } else if (stored === 'light') {
    applyTheme(false)
  } else {
    // Aucune préférence stockée : respecter prefers-color-scheme
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    applyTheme(prefersDark)
  }
})
</script>

<style scoped>
.theme-switcher {
  position: fixed;
  top: 60px;
  inset-inline-end: 12px;
  z-index: var(--ms-z-floating-lang, 1500);

  display: inline-flex;
  align-items: center;
  justify-content: center;

  width: 40px;
  height: 40px;
  padding: 0;

  background: var(--ms-bg-elevated, #ffffff);
  border: 1.5px solid var(--ms-border-strong, rgba(42, 42, 53, 0.16));
  border-radius: var(--ms-radius-pill, 999px);
  box-shadow: var(--ms-shadow-md, 0 4px 16px rgba(42, 42, 53, 0.06));
  cursor: pointer;

  transition:
    background var(--ms-transition, 200ms),
    border-color var(--ms-transition, 200ms),
    transform var(--ms-transition, 200ms),
    box-shadow var(--ms-transition, 200ms);
}

.theme-switcher:hover {
  background: var(--ms-bg-muted, #f2eee6);
  border-color: var(--ms-orange, #ff8551);
  transform: translateY(-2px);
  box-shadow: var(--ms-shadow-orange, 0 6px 18px rgba(255, 133, 81, 0.28));
}

.theme-switcher:focus-visible {
  outline: 3px solid var(--ms-border-focus, rgba(255, 133, 81, 0.45));
  outline-offset: 2px;
}

.theme-switcher__icon {
  font-size: 16px;
  line-height: 1;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .theme-switcher {
    transition: none;
  }
}
</style>
