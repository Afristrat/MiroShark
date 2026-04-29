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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
