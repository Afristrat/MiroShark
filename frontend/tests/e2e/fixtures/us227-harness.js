import { createApp } from 'vue'
import i18n from '/src/i18n.js'
import PolymarketChart from '/src/components/PolymarketChart.vue'

export function mountUs227({ live = false } = {}) {
  document.body.innerHTML = '<div id="app"></div>'
  const app = createApp(PolymarketChart, {
    simulationId: 'sim-us227',
    visible: true,
    live,
  })
  app.use(i18n)
  app.mount('#app')
}
