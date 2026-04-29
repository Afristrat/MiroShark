<template>
  <div class="lang-switcher" :class="{ 'is-open': isOpen }">
    <button
      ref="toggleEl"
      type="button"
      class="lang-switcher__toggle"
      :aria-label="t('language.switch')"
      :aria-expanded="isOpen ? 'true' : 'false'"
      aria-haspopup="listbox"
      @click="toggle"
    >
      <span class="lang-switcher__flag" aria-hidden="true">{{ flagFor(current) }}</span>
      <span class="lang-switcher__code">{{ current.toUpperCase() }}</span>
      <span class="lang-switcher__caret" aria-hidden="true">▾</span>
    </button>

    <ul
      v-if="isOpen"
      class="lang-switcher__menu"
      role="listbox"
      :aria-label="t('language.switch')"
    >
      <li
        v-for="loc in locales"
        :key="loc"
        class="lang-switcher__option"
        :class="{ 'is-active': loc === current }"
        role="option"
        :aria-selected="loc === current ? 'true' : 'false'"
        :tabindex="0"
        @click="select(loc)"
        @keydown.enter.prevent="select(loc)"
        @keydown.space.prevent="select(loc)"
      >
        <span class="lang-switcher__flag" aria-hidden="true">{{ flagFor(loc) }}</span>
        <span class="lang-switcher__name">{{ nameFor(loc) }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import i18nInstance, { setLocale, SUPPORTED_LOCALES } from '../i18n'

const { locale, t } = useI18n()

const isOpen = ref(false)
const toggleEl = ref(null)
const locales = SUPPORTED_LOCALES
const current = computed(() => locale.value)

const FLAGS = { fr: '🇫🇷', ar: '🇲🇦', en: '🇬🇧' }

function flagFor(loc) { return FLAGS[loc] || '🌐' }
function nameFor(loc) { return t(`language.${loc}`) }

function toggle() { isOpen.value = !isOpen.value }
function close() { isOpen.value = false }

function select(loc) {
  setLocale(i18nInstance, loc)
  close()
  if (toggleEl.value) toggleEl.value.focus()
}

function onClickOutside(e) {
  if (!e.target.closest('.lang-switcher')) close()
}

function onKeydown(e) {
  if (e.key === 'Escape') close()
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.lang-switcher {
  position: relative;
  display: inline-flex;
  font-family: var(--ms-font-body, system-ui, sans-serif);
}

.lang-switcher__toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--ms-bg-elevated, #fff);
  color: var(--ms-text, #2A2A35);
  border: 1px solid var(--ms-border-strong, rgba(42, 42, 53, 0.16));
  border-radius: var(--ms-radius-pill, 999px);
  cursor: pointer;
  font-size: var(--ms-text-sm, 13px);
  font-weight: 600;
  line-height: 1.2;
  box-shadow: var(--ms-shadow-sm, 0 2px 8px rgba(42, 42, 53, 0.05));
  transition:
    background var(--ms-transition, 200ms),
    border-color var(--ms-transition, 200ms),
    transform var(--ms-transition, 200ms);
}

.lang-switcher__toggle:hover {
  background: var(--ms-bg-muted, #F2EEE6);
  border-color: var(--ms-text-muted, #6B6B7D);
  transform: translateY(-1px);
}

.lang-switcher__toggle:focus-visible {
  outline: 3px solid var(--ms-border-focus, rgba(255, 133, 81, 0.45));
  outline-offset: 2px;
}

.is-open .lang-switcher__toggle {
  background: var(--ms-bg-muted, #F2EEE6);
  border-color: var(--ms-text-muted, #6B6B7D);
}

.lang-switcher__flag { font-size: 14px; line-height: 1; }
.lang-switcher__code { letter-spacing: 0.04em; }
.lang-switcher__caret { font-size: 10px; opacity: 0.6; }

.lang-switcher__menu {
  position: absolute;
  top: calc(100% + 6px);
  inset-inline-end: 0;
  min-width: 168px;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--ms-bg-elevated, #fff);
  border: 1px solid var(--ms-border, rgba(42, 42, 53, 0.08));
  border-radius: var(--ms-radius-md, 12px);
  box-shadow: var(--ms-shadow-lg, 0 12px 32px rgba(42, 42, 53, 0.08));
  z-index: 1000;
}

.lang-switcher__option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--ms-radius-sm, 8px);
  cursor: pointer;
  font-size: var(--ms-text-sm, 13px);
  color: var(--ms-text, #2A2A35);
  transition: background var(--ms-transition, 200ms);
}

.lang-switcher__option:hover,
.lang-switcher__option:focus-visible {
  background: var(--ms-bg-muted, #F2EEE6);
  outline: none;
}

.lang-switcher__option.is-active {
  background: var(--ms-orange-soft, rgba(255, 133, 81, 0.12));
  font-weight: 600;
}
</style>
