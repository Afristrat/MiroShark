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
    // Public methodology page — remplace l'ancienne page calibration
    // (US-201, ADR-002) : la transparence méthode + limites EST l'argument
    // commercial ; plus aucun claim chiffré non étayé. Alias conservé pour
    // les liens externes historiques vers /calibration.
    path: '/methodologie',
    alias: '/calibration',
    name: 'Methodologie',
    component: () => import('../views/MethodologieView.vue')
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
  },
  {
    // US-107 — Console upload privative. Extraite de Home.vue, séparée
    // proprement derrière requiresAuth + requiresSelfService (super-admin
    // OU org avec self_service_enabled = true).
    path: '/console',
    name: 'Console',
    component: () => import('../views/ConsoleView.vue'),
    meta: {
      requiresAuth: true,
      requiresSelfService: true,
      title: 'Console · Bassira'
    }
  },
  {
    // US-102 — Console super-admin pour gérer les devis (quotes).
    // Tableau + modal détail + workflow statut + envoi Stripe Payment Link.
    path: '/admin/quotes',
    name: 'AdminQuotes',
    component: () => import('../views/AdminQuotesView.vue'),
    meta: {
      requiresAuth: true,
      requiresSuperAdmin: true,
      title: 'Devis · Bassira admin'
    }
  },
  {
    // US-115 — Gestion des invitations org → user. Accessible aux
    // admin/owner d'une org (et aux super-admins). Form + liste pending.
    path: '/admin/invitations',
    name: 'AdminInvitations',
    component: () => import('../views/AdminInvitationsView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Invitations · Bassira admin'
    }
  },
  {
    // US-120 — Gestion du branding PDF par org (super-admin uniquement).
    // Table des configurations + form modal create/edit + preview SVG live.
    path: '/admin/branding',
    name: 'AdminBranding',
    component: () => import('../views/AdminBrandingView.vue'),
    meta: {
      requiresAuth: true,
      requiresSuperAdmin: true,
      title: 'Branding PDF · Bassira admin'
    }
  },
  {
    // US-137 — Liste cross-tenant des inscriptions (super-admin OU org admin).
    // Stats globales + filtres org/email + modal simulations + modal profil.
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/AdminUsersView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Utilisateurs · Bassira admin'
    }
  },
  {
    // ADR-IQ-08 — Escalades silencieuses + playbook vivant de l'agent Intake.
    path: '/admin/agent-playbook',
    name: 'AdminAgentPlaybook',
    component: () => import('../views/AdminAgentPlaybookView.vue'),
    meta: {
      requiresAuth: true,
      requiresSuperAdmin: true,
      title: 'Playbook agent · Bassira admin'
    }
  },
  {
    // US-127 — Révision rapport (split view PDF + Tiptap + CodeMirror + diff versioning).
    path: '/admin/reports/:id/review',
    name: 'AdminReportReview',
    component: () => import('../views/AdminReportReviewView.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      requiresSuperAdmin: true,
      title: 'Révision rapport · Bassira admin'
    }
  },
  {
    // US-130 — Suivi des livraisons + tracking téléchargements (super-admin).
    path: '/admin/reports/:id/tracking',
    name: 'AdminReportTracking',
    component: () => import('../views/AdminReportTrackingView.vue'),
    props: true,
    meta: {
      requiresAuth: true,
      requiresSuperAdmin: true,
      title: 'Suivi livraisons · Bassira admin'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// US-093 — guard global : protège les routes meta.requiresAuth.
// US-107 — étendu pour requiresSelfService (super-admin OU
//   currentOrg.self_service_enabled).
// US-102 — étendu pour requiresSuperAdmin.
// Si non authentifié → redirection vers /login avec ?redirect=<path>.
// On lit l'auth store (Pinia) ; init() est appelé en amont depuis main.js
// donc l'état de session persisté est déjà chargé au moment des nav.
router.beforeEach(async (to) => {
  // US-096 fix — Si on revient d'un OAuth implicit (URL contient
  // `#access_token=...`), Supabase JS est en train d'écrire la session ;
  // ne pas rediriger vers /login dans cette fenêtre.
  if (typeof window !== 'undefined' && window.location.hash.includes('access_token=')) {
    return true
  }

  const needsAuth = to.meta?.requiresAuth || to.meta?.requiresSelfService || to.meta?.requiresSuperAdmin
  if (!needsAuth) return true

  const auth = useAuthStore()
  if (!auth.isAuthenticated) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath }
    }
  }

  // US-107 — guard self-service : super-admin OU org avec flag activé.
  if (to.meta?.requiresSelfService) {
    const ok = auth.isSuperAdmin || Boolean(auth.currentOrg?.self_service_enabled)
    if (!ok) {
      return {
        path: '/client/dashboard',
        query: { reason: 'no-self-service' }
      }
    }
  }

  // US-102 — guard super-admin : front cache l'UI, backend reste seul juge.
  if (to.meta?.requiresSuperAdmin) {
    if (!auth.isSuperAdmin) {
      return {
        path: '/client/dashboard',
        query: { reason: 'not-super-admin' }
      }
    }
  }

  return true
})

export default router
