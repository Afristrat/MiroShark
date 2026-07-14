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

// Interceptor request : Bearer token + locale + X-Org-Id.
client.interceptors.request.use(
  (config) => {
    try {
      const auth = useAuthStore()
      const token = auth.session?.access_token
      if (token) {
        config.headers = config.headers || {}
        config.headers['Authorization'] = `Bearer ${token}`
      }
      // Bug 2 — propage l'org courante au backend pour les endpoints
      // multi-tenant (@require_org_membership) qui rejettent les users
      // multi-org sans hint explicite. Le header est ignoré par les
      // endpoints qui n'en ont pas besoin.
      const orgId = auth.currentOrgId
      if (orgId) {
        config.headers = config.headers || {}
        if (!config.headers['X-Org-Id']) {
          config.headers['X-Org-Id'] = orgId
        }
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

/** GET /api/client/quotes — liste les devis de l'org courante (Lot B, US-B4). */
export function listClientQuotes(params = {}) {
  return client.get('/api/client/quotes', { params })
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
 * PATCH /api/admin/organizations/<orgId>/self-service — toggle self-service (US-098).
 *
 * Reservé aux super-admins. Body : `{ enabled: boolean }`.
 *
 * Returns: `{ org_id, self_service_enabled: bool }`
 */
export function setOrgSelfService(orgId, enabled) {
  return client.patch(
    `/api/admin/organizations/${encodeURIComponent(orgId)}/self-service`,
    { enabled: Boolean(enabled) }
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

// ───── Super-admin Bassira — Quotes (US-102 / US-103 / US-104) ──────────────

/**
 * GET /api/admin/quotes — liste paginée des devis reçus.
 * Filtres : limit, offset, status (received|reviewing|quoted|...).
 */
export function fetchAdminQuotes(filters = {}) {
  const params = {}
  if (typeof filters.limit === 'number') params.limit = filters.limit
  if (typeof filters.offset === 'number') params.offset = filters.offset
  if (filters.status) params.status = filters.status
  return client.get('/api/admin/quotes', { params })
}

/** GET /api/admin/quotes/<id> — détail d'un devis. */
export function fetchAdminQuoteDetail(quoteId) {
  return client.get(`/api/admin/quotes/${encodeURIComponent(quoteId)}`)
}

/**
 * PATCH /api/admin/quotes/<id>/status — transition workflow (US-103).
 * Body : { status, notes?, payment_link?, delivered_url? }
 */
export function patchAdminQuoteStatus(quoteId, payload) {
  return client.patch(
    `/api/admin/quotes/${encodeURIComponent(quoteId)}/status`,
    payload
  )
}

/** PATCH /api/admin/quotes/<id>/notes — notes admin libre (US-103). */
export function patchAdminQuoteNotes(quoteId, notes) {
  return client.patch(
    `/api/admin/quotes/${encodeURIComponent(quoteId)}/notes`,
    { notes }
  )
}

/**
 * POST /api/admin/quotes/<id>/send-payment-link — envoie l'email Stripe (US-104).
 * Transition automatique vers `quoted`.
 */
export function sendAdminQuotePaymentLink(quoteId, payload) {
  return client.post(
    `/api/admin/quotes/${encodeURIComponent(quoteId)}/send-payment-link`,
    payload
  )
}

/**
 * POST /api/admin/quotes/<id>/send-delivered — envoie l'email de livraison (US-104).
 * Transition automatique vers `delivered`.
 */
export function sendAdminQuoteDelivered(quoteId, payload) {
  return client.post(
    `/api/admin/quotes/${encodeURIComponent(quoteId)}/send-delivered`,
    payload
  )
}

// ───── Invitations org → user (US-115) ─────────────────────────────────────

/**
 * GET /api/admin/invitations — liste les invitations pending d'une org.
 * Param `org_id` requis si super-admin OR multi-org admin.
 */
export function fetchAdminInvitations(params = {}) {
  return client.get('/api/admin/invitations', { params })
}

/**
 * POST /api/admin/invitations — crée une invitation + envoie l'email.
 * Body : { email, role: 'member'|'admin'|'viewer', org_id? }
 */
export function createAdminInvitation(payload) {
  return client.post('/api/admin/invitations', payload)
}

/** DELETE /api/admin/invitations/<token> — révoque une invitation pending. */
export function revokeAdminInvitation(token) {
  return client.delete(
    `/api/admin/invitations/${encodeURIComponent(token)}`
  )
}

/**
 * GET /api/invitations/<token>/accept — public, lit les metadata
 * d'une invitation (org_name, role, expires_at) pour pré-remplir
 * l'écran signup. Pas de bearer requis.
 */
export function fetchInvitationMetadata(token) {
  return client.get(
    `/api/invitations/${encodeURIComponent(token)}/accept`
  )
}

/**
 * POST /api/invitations/<token>/redeem — auth requis, crée la row
 * org_members atomiquement après signup.
 */
export function redeemInvitation(token) {
  return client.post(
    `/api/invitations/${encodeURIComponent(token)}/redeem`
  )
}

// ───── PDF Branding admin (US-120) ─────────────────────────────────────────

/**
 * GET /api/admin/branding — liste les brandings PDF d'une org (toutes versions).
 * Params : org_id (requis si super-admin ou multi-org admin), limit, offset.
 */
export function fetchAdminBrandings(params = {}) {
  return client.get('/api/admin/branding', { params })
}

/**
 * POST /api/admin/branding — crée un nouveau branding PDF.
 * Body : { org_id?, name, logo_url?, header_*, footer_*, palette_*, font_*, disclaimer_text? }
 */
export function createAdminBranding(payload) {
  return client.post('/api/admin/branding', payload)
}

/**
 * PATCH /api/admin/branding/<id> — met à jour un branding (versioning insert).
 * Body : champs à modifier (tous optionnels sauf au moins un requis).
 */
export function patchAdminBranding(brandingId, payload) {
  return client.patch(
    `/api/admin/branding/${encodeURIComponent(brandingId)}`,
    payload
  )
}

/**
 * POST /api/admin/branding/<id>/preview — génère un aperçu SVG du branding.
 * Body : { lang: 'fr' | 'en' | 'ar' }
 * Retourne : { preview_svg: '<base64>', content_type: 'image/svg+xml', lang }
 */
export function previewAdminBranding(brandingId, lang = 'fr') {
  return client.post(
    `/api/admin/branding/${encodeURIComponent(brandingId)}/preview`,
    { lang }
  )
}

// ───── Admin Users — liste cross-tenant (US-137) ───────────────────────────

/**
 * GET /api/admin/users — liste paginée des inscriptions.
 * Filtres : org_id, search (email), limit, offset.
 * Super-admin : cross-tenant. Org admin : scopé à ses orgs.
 *
 * Returns: `{ users: [...], total: N, limit: N, offset: N }`
 */
export function fetchAdminUsers(filters = {}) {
  const params = {}
  if (filters.org_id) params.org_id = filters.org_id
  if (filters.search) params.search = filters.search
  if (typeof filters.limit === 'number' && filters.limit > 0) params.limit = filters.limit
  if (typeof filters.offset === 'number' && filters.offset >= 0) params.offset = filters.offset
  return client.get('/api/admin/users', { params })
}

/**
 * GET /api/admin/users/stats — statistiques globales des inscriptions.
 *
 * Returns: `{ total_users: N, active_7d: N, new_30d: N, by_org: {...} }`
 */
export function fetchAdminUsersStats() {
  return client.get('/api/admin/users/stats')
}

/**
 * GET /api/admin/users/<user_id>/simulations — liste des simulations d'un user.
 * Params : limit, offset.
 *
 * Returns: `{ simulations: [...], total: N, user_id: "uuid" }`
 */
export function fetchAdminUserSimulations(userId, params = {}) {
  return client.get(
    `/api/admin/users/${encodeURIComponent(userId)}/simulations`,
    { params }
  )
}

// ── US-138 — gestion des memberships utilisateur ↔ organisation ─────────────

/**
 * POST /api/admin/users/<user_id>/orgs — affecte (ou met à jour) un user
 * dans une organisation. Idempotent.
 *
 * Body : `{ org_id, role: 'member'|'admin'|'owner' }`
 * Returns: `{ user_id, org_id, role }`
 */
export function addUserToOrg(userId, orgId, role = 'member') {
  return client.post(
    `/api/admin/users/${encodeURIComponent(userId)}/orgs`,
    { org_id: orgId, role }
  )
}

/**
 * DELETE /api/admin/users/<user_id>/orgs/<org_id> — retire la membership.
 * 409 LAST_OWNER si c'est le dernier owner de l'org.
 */
export function removeUserFromOrg(userId, orgId) {
  return client.delete(
    `/api/admin/users/${encodeURIComponent(userId)}/orgs/${encodeURIComponent(orgId)}`
  )
}

/**
 * POST /api/admin/organizations — crée une nouvelle organisation (super-admin).
 *
 * Body : `{ name, slug?, country_code?, sector?, self_service_enabled? }`
 * Le caller est automatiquement ajouté comme owner.
 * Returns: l'organisation créée (id, slug, name, ...).
 */
export function createOrganization(payload) {
  return client.post('/api/admin/organizations', payload)
}

// ───── Agent Intake — playbook + escalades (ADR-IQ-08) ─────────────────────

/**
 * GET /api/admin/quotes/intake/escalations — liste les escalades de l'agent
 * Intake (ADR-IQ-08). Query : { unreviewed_only? }
 */
export function fetchIntakeEscalations(params = {}) {
  return client.get('/api/admin/quotes/intake/escalations', { params })
}

/**
 * PATCH /api/admin/quotes/intake/escalations/<id> — marque une escalade revue.
 * Body : { reviewer_note? }
 */
export function reviewIntakeEscalation(escalationId, payload = {}) {
  return client.patch(
    `/api/admin/quotes/intake/escalations/${encodeURIComponent(escalationId)}`,
    payload
  )
}

/**
 * GET /api/admin/quotes/intake/playbook — liste les entrées du playbook.
 */
export function fetchIntakePlaybook() {
  return client.get('/api/admin/quotes/intake/playbook')
}

/**
 * POST /api/admin/quotes/intake/playbook — ajoute une correction.
 * Body : { situation_pattern, corrected_response }
 */
export function createIntakePlaybookEntry(payload) {
  return client.post('/api/admin/quotes/intake/playbook', payload)
}

/**
 * PATCH /api/admin/quotes/intake/playbook/<id> — active/désactive une entrée.
 * Body : { active }
 */
export function toggleIntakePlaybookEntry(entryId, active) {
  return client.patch(
    `/api/admin/quotes/intake/playbook/${encodeURIComponent(entryId)}`,
    { active }
  )
}

export default client
