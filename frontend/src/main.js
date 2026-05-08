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
//
// US-138 — on AWAIT aussi fetchSuperStatus() si une session est active,
// pour que les routes /admin/* (requiresSuperAdmin) ne flickent plus
// vers /login lors du tout premier mount du router. Sans ce await, le
// guard se déclenche avec isSuperAdminFlag=false et redirige vers
// /client/dashboard ou /login le temps que la requête /api/admin/me/super-status
// résolve, puis l'utilisateur revient sur la bonne page — UX cassée.
import { useAuthStore } from './stores/auth'
;(async () => {
  try {
    const auth = useAuthStore()
    await auth.init()
    if (auth.isAuthenticated) {
      // fail-soft : si fetchSuperStatus échoue on monte quand même.
      try {
        await auth.fetchSuperStatus()
      } catch (e) {
        console.warn('[Bassira] fetchSuperStatus pre-mount failed:', e)
      }
    }
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
