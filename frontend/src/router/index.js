import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import { useAuthStore } from '../stores/auth'

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
  },
  {
    // Vitrine /models publique (US-086) — 5 modèles stratégiques
    // pré-calibrés productivisés. Cible C-level institutionnel.
    path: '/models',
    name: 'ModelsList',
    component: () => import('../views/ModelsListView.vue'),
    meta: { title: 'Modèles stratégiques · Bassira' }
  },
  {
    // Détail d'un modèle stratégique (US-086) — 7 sections narratives.
    path: '/models/:slug',
    name: 'ModelDetail',
    component: () => import('../views/ModelDetailView.vue'),
    props: true,
    meta: { title: 'Modèle · Bassira' }
  },
  {
    // Auth (US-093) — login Supabase pour comptes clients.
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Se connecter · Bassira' }
  },
  {
    // Auth (US-093) — création de compte. L'attribution à une org se fait
    // manuellement par l'équipe Bassira (cf. supabase/seed.sql) tant que
    // le flow d'invitation auto n'est pas en place.
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
    meta: { title: 'Créer un compte · Bassira' }
  },
  {
    // Espace privatif client (US-093) — table des simulations + outcomes
    // + publish, scopée à l'org courante via RLS Supabase.
    path: '/client/dashboard',
    name: 'ClientDashboard',
    component: () => import('../views/ClientDashboardView.vue'),
    meta: { requiresAuth: true, title: 'Mon espace · Bassira' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// US-093 — guard global : protège les routes meta.requiresAuth.
// Si non authentifié → redirection vers /login avec ?redirect=<path>.
// On lit l'auth store (Pinia) ; init() est appelé en amont depuis main.js
// donc l'état de session persisté est déjà chargé au moment des nav.
router.beforeEach(async (to) => {
  if (!to.meta?.requiresAuth) return true
  // US-096 fix — Si on revient d'un OAuth implicit (URL contient
  // `#access_token=...`), Supabase JS est en train d'écrire la session ;
  // ne pas rediriger vers /login dans cette fenêtre. auth.init() côté
  // store attend déjà l'event SIGNED_IN — ce garde-fou est une 2e ligne
  // de défense au cas où le router naviguerait avant que init() finisse.
  if (typeof window !== 'undefined' && window.location.hash.includes('access_token=')) {
    return true
  }
  const auth = useAuthStore()
  if (!auth.isAuthenticated) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath }
    }
  }
  return true
})

export default router
