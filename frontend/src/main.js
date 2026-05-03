import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

// Design system « Playful & Soft » — tokens + utilitaires .ms-*
// Importé ici pour précéder le <style> global de App.vue (legacy compat conservé).
import './design-tokens.css'
import './styles/components.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)

// US-093 — initialise le store auth (récupère la session Supabase
// persistée + abonne le listener onAuthStateChange) AVANT de monter
// l'app, pour que les guards router beforeEach voient l'état réel.
// On utilise une IIFE async ; en cas d'échec réseau on monte quand même
// (les routes publiques restent accessibles).
import { useAuthStore } from './stores/auth'
;(async () => {
  try {
    const auth = useAuthStore()
    await auth.init()
  } catch (err) {
    console.warn('[Bassira] auth init failed (mounting anyway):', err)
  } finally {
    app.mount('#app')
  }
})()

// Register service worker for browser push notifications
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch((err) => {
    console.warn('[Bassira] Service worker registration failed:', err)
  })
}
