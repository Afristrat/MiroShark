import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

// Design system « Playful & Soft » — tokens + utilitaires .ms-*
// Importé ici pour précéder le <style> global de App.vue (legacy compat conservé).
import './design-tokens.css'
import './styles/components.css'

const app = createApp(App)

app.use(router)
app.use(i18n)

app.mount('#app')

// Register service worker for browser push notifications
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch((err) => {
    console.warn('[Bassira] Service worker registration failed:', err)
  })
}
