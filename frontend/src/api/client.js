/**
 * Bassira — API client privatif (US-093)
 * ─────────────────────────────────────────────────────────────────────
 * Wrapper axios qui injecte automatiquement `Authorization: Bearer
 * <session.access_token>` sur les requêtes vers /api/auth/* et
 * /api/client/*. Lit le token depuis le store Pinia auth.
 *
 * Endpoints visés (contrat US-092) :
 *   - GET    /api/auth/me
 *   - GET    /api/client/simulations
 *   - POST   /api/client/simulations
 *   - POST   /api/client/simulations/:id/outcome
 *   - POST   /api/client/simulations/:id/publish
 *   - GET    /api/calibration/aggregates  (public, sans bearer)
 *
 * NB : on réutilise pas l'axios de api/index.js car ce dernier a une
 * logique d'interceptor d'erreur qui rejette quand `success: false`,
 * incompatible avec les nouvelles réponses qui peuvent être un objet
 * direct. On garde un axios séparé, plus simple, pour les endpoints
 * privatifs.
 */

import axios from 'axios'
import i18nInstance from '../i18n'
import { useAuthStore } from '../stores/auth'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor request : Bearer token + locale.
client.interceptors.request.use(
  (config) => {
    try {
      const auth = useAuthStore()
      const token = auth.session?.access_token
      if (token) {
        config.headers = config.headers || {}
        config.headers['Authorization'] = `Bearer ${token}`
      }
    } catch (_) {
      // Pinia pas encore initialisé (rarissime au boot) — on continue
      // sans bearer ; le backend renverra 401 et l'UI redirigera.
    }
    try {
      const locale = i18nInstance.global?.locale?.value || 'fr'
      config.headers = config.headers || {}
      config.headers['X-Bassira-Locale'] = locale
    } catch (_) {
      /* i18n pas prêt — backend défaut fr */
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Interceptor response : extrait .data ou propage erreur HTTP.
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Token expiré ou invalide — l'app devrait rediriger vers /login.
      // On ne fait pas la redirection ici (séparation des responsabilités) :
      // les vues capturent l'erreur et déclenchent le flow approprié.
      console.warn('[Bassira client] 401 unauthorized')
    }
    return Promise.reject(error)
  }
)

// ───── Méthodes typées ───────────────────────────────────────────────

/** GET /api/client/auth/me — retourne le profil multitenant de l'user courant.
 *  Le blueprint backend client_bp est monté au préfixe /api/client/, donc le
 *  chemin effectif inclut /client/ (cf. US-092 backend/app/__init__.py). */
export function fetchMe() {
  return client.get('/api/client/auth/me')
}

/** GET /api/client/simulations — liste les simulations de l'org courante. */
export function listClientSimulations(params = {}) {
  return client.get('/api/client/simulations', { params })
}

/** POST /api/client/simulations — crée une simulation (commande). */
export function createClientSimulation(payload) {
  return client.post('/api/client/simulations', payload)
}

/**
 * POST /api/client/simulations/:id/outcome — marque l'issue d'une sim.
 * payload: { label: 'called_it'|'partial'|'wrong', observed_at, source_url, notes }
 */
export function markOutcome(simulationId, payload) {
  return client.post(
    `/api/client/simulations/${encodeURIComponent(simulationId)}/outcome`,
    payload
  )
}

/**
 * POST /api/client/simulations/:id/publish — bascule is_published.
 * payload: { is_published: boolean }
 */
export function publishSimulation(simulationId, payload = { is_published: true }) {
  return client.post(
    `/api/client/simulations/${encodeURIComponent(simulationId)}/publish`,
    payload
  )
}

/**
 * GET /api/calibration/aggregates — vue publique k-anonymity n≥5.
 * Pas de bearer requis (route publique). On utilise le même client
 * pour cohérence (l'interceptor n'ajoute le token que s'il existe).
 */
export function fetchPublicCalibrationAggregates() {
  return client.get('/api/calibration/aggregates')
}

// ───── Super-admin Bassira (US-095) ──────────────────────────────────
//
// Ces endpoints exigent un JWT Supabase ET un email figurant dans la
// whitelist backend `BASSIRA_SUPER_ADMIN_EMAILS`. Le frontend ne dispose
// d'AUCUN secret super-admin — la décision d'autorisation reste
// 100 % côté backend (zero-trust côté navigateur).

/**
 * GET /api/admin/me/super-status — révèle si l'user est super-admin.
 *
 * Auth requise (JWT Supabase) mais pas le rôle super-admin lui-même.
 * Permet au frontend de conditionner l'affichage de l'entrée nav
 * « Admin » et de la section « Toutes les organisations ».
 *
 * Returns: `{ is_super_admin: boolean, email: string }`
 */
export function fetchSuperStatus() {
  return client.get('/api/admin/me/super-status')
}

/**
 * GET /api/admin/organizations — liste TOUTES les organisations Bassira.
 *
 * Reservé aux super-admins. Si l'user n'est pas whitelist : 403 NOT_SUPER_ADMIN.
 *
 * Returns: `{ organizations: [{id, slug, name, sector, country_code,
 *   status, created_at, members_count, simulations_count, published_count,
 *   avg_brier}, ...] }`
 */
export function fetchAllOrganizations() {
  return client.get('/api/admin/organizations')
}

/**
 * GET /api/admin/organizations/<orgId> — détail d'une organisation.
 *
 * Reservé aux super-admins. Retourne metadata + members + simulations.
 *
 * Returns: `{ organization: {...}, members: [...], simulations: [...] }`
 */
export function fetchOrganizationDetail(orgId) {
  return client.get(
    `/api/admin/organizations/${encodeURIComponent(orgId)}`
  )
}

/**
 * GET /api/admin/simulations — liste TOUTES les simulations cross-tenant (US-097).
 *
 * Reservé aux super-admins. Filtres optionnels passés via params :
 *   - org_id, package_id, published (true|false), limit (default 50, max 200), offset
 *
 * Returns: `{ simulations: [{simulation_id, org_id, org_name, org_slug,
 *   created_by, created_at, package_id, is_published, outcome,
 *   brier_score}, ...], total: int, limit: int, offset: int }`
 */
export function fetchAllSimulations(filters = {}) {
  const params = {}
  if (filters.org_id) params.org_id = filters.org_id
  if (filters.package_id) params.package_id = filters.package_id
  if (filters.published === true) params.published = 'true'
  if (filters.published === false) params.published = 'false'
  if (typeof filters.limit === 'number' && filters.limit > 0) {
    params.limit = filters.limit
  }
  if (typeof filters.offset === 'number' && filters.offset >= 0) {
    params.offset = filters.offset
  }
  return client.get('/api/admin/simulations', { params })
}

export default client
