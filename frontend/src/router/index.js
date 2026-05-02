import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: () => import('../views/MainView.vue'),
    props: true
  },
  {
    // US-040 — Step 1.5 « Review & refine entities » between graph build
    // and agent setup. Lists the generated entities grouped by type with
    // inline rename / merge / delete / add actions. « Looks good » sends
    // the user back to the project workbench so Step 2 can resume.
    path: '/review-entities/:projectId',
    name: 'ReviewEntities',
    component: () => import('../views/ReviewEntitiesView.vue'),
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: () => import('../views/SimulationView.vue'),
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: () => import('../views/SimulationRunView.vue'),
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: () => import('../views/ReportView.vue'),
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: () => import('../views/InteractionView.vue'),
    props: true
  },
  {
    path: '/replay/:simulationId',
    name: 'Replay',
    component: () => import('../views/ReplayView.vue'),
    props: true
  },
  {
    path: '/compare/:id1?/:id2?',
    name: 'Compare',
    component: () => import('../views/ComparisonView.vue'),
    props: true
  },
  {
    path: '/embed/:simulationId',
    name: 'Embed',
    component: () => import('../views/EmbedView.vue'),
    props: true
  },
  {
    path: '/explore',
    name: 'Explore',
    component: () => import('../views/ExploreView.vue')
  },
  {
    // Dedicated URL for the "Verified Prediction" hall — same component
    // as /explore but with the verified filter pre-applied. Keep it as a
    // top-level path so it's a clean link to drop into threads about
    // pre-incident simulations.
    path: '/verified',
    name: 'Verified',
    component: () => import('../views/ExploreView.vue'),
    props: { verifiedOnly: true }
  },
  {
    // Public calibration page — Brier score + calibration plot served
    // as the commercial argument. No auth wall by design (US-021).
    path: '/calibration',
    name: 'Calibration',
    component: () => import('../views/CalibrationView.vue')
  },
  {
    // Public commercial landing — 3 service packages (US-023). Pas de
    // backend pour cette route ; les CTA pointent vers /devis (US-025)
    // ou retombent sur un mailto si la route n'est pas encore montée.
    path: '/offres',
    name: 'Offers',
    component: () => import('../views/OffersView.vue')
  },
  {
    // Tunnel commercial — formulaire multi-step de demande de devis
    // (US-025). Atteint depuis /offres via les CTA « Demander un devis ».
    // Query param ``?package=`` pré-remplit le sélecteur du Step 2.
    path: '/devis',
    name: 'Quote',
    component: () => import('../views/QuoteView.vue')
  },
  {
    // Landing page SEO marketing (US-061) — séparée de Home.vue.
    // Optimisée pour cold traffic LinkedIn/Google. CTAs vers /devis et /explore.
    path: '/landing',
    name: 'Landing',
    component: () => import('../views/LandingView.vue')
  },
  {
    // Page partenariats institutionnels (US-062) — think tanks, cabinets
    // conseil, universités. 3 tiers (Research / Integration / White-label).
    // Registre académique — JAMAIS de language startup.
    path: '/partenaires',
    name: 'Partners',
    component: () => import('../views/PartnersView.vue')
  },
  {
    // Tableau analytique interne admin (US-065) — auth via
    // BASSIRA_ADMIN_TOKEN sessionStorage. KPIs plateforme + funnel +
    // top packages + time series 30j. Vue dark-mode par défaut.
    path: '/admin/analytics',
    name: 'AdminAnalytics',
    component: () => import('../views/AnalyticsView.vue'),
    meta: { requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
