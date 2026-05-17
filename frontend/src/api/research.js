/**
 * US-B01/B02 — Client API recherche dynamique seed → topics.
 *
 * Wrappe les deux endpoints Bassira proxy → Kairos :
 *   POST /api/research/from-seed   → { session_id, status, cached, message }
 *   GET  /api/research/status      → { session_id, status, result, … }
 *
 * On réutilise le client privatif Bassira (`api/client.js`) — donc Bearer
 * Supabase auto-injecté + locale header + interceptor d'erreur 401.
 *
 * Les méthodes retournent le payload `data` extrait (l'interceptor de
 * client.js renvoie déjà `response.data`, donc on a la forme
 * `{ success, data, … }`). On laisse au consommateur le soin de tester
 * `success` et de mapper `error_code` → message i18n.
 */

import client from './client'

/**
 * POST /api/research/from-seed — soumet une graine au pipeline Kairos.
 *
 * @param {Object} payload
 * @param {string} payload.seed - 50-3000 caractères
 * @param {'fr'|'en'|'ar'} payload.lang
 * @param {string} [payload.sector_hint]
 * @param {0|1|2} [payload.depth_hint]
 * @param {string} [payload.scope_profile] - nom d'un scope_profile pré-curé
 *   côté Kairos (ex: 'morocco-tech', 'mena-business'). Force la coverage
 *   sur des sources spécialisées.
 * @param {{x_handles?: string[], reddit_subs?: string[], arxiv_categories?: string[], rss_keywords?: string[]}} [payload.hints_override]
 *   Sources fournies directement par l'utilisateur (mergées avec celles
 *   émises par research-strategist + scope_profile).
 * @returns {Promise<{success: boolean, data?: {session_id, status, cached, message}, error_code?: string, error?: string}>}
 */
export function postResearchFromSeed(payload) {
  return client.post('/api/research/from-seed', payload)
}

/**
 * GET /api/research/scope-profiles — liste les profils de coverage publics
 * disponibles côté Kairos (morocco-tech, mena-business, etc.).
 *
 * @returns {Promise<{success: boolean, data?: {profiles: Array<{name, description, reddit_subs, arxiv_categories, rss_keywords}>, count, cached}, error_code?: string}>}
 */
export function getScopeProfiles() {
  return client.get('/api/research/scope-profiles')
}

/**
 * GET /api/research/status?session_id=… — polling.
 *
 * @param {string} sessionId - UUID Kairos
 * @returns {Promise<{success: boolean, data?: {session_id, status, result?, error_detail?, telemetry?, created_at, completed_at, cached}, error_code?: string, error?: string}>}
 */
export function getResearchStatus(sessionId) {
  return client.get('/api/research/status', {
    params: { session_id: sessionId },
  })
}

/**
 * Map les error_codes backend → clé i18n research.errors.* à afficher.
 * Les codes inconnus tombent sur `generic`.
 *
 * @param {string|undefined|null} code
 * @returns {string} clé i18n (à passer à $t)
 */
export function researchErrorKeyForCode(code) {
  if (!code) return 'research.errors.generic'
  const map = {
    KAIROS_NOT_CONFIGURED: 'research.errors.notConfigured',
    KAIROS_UNREACHABLE: 'research.errors.unreachable',
    KAIROS_TIMEOUT: 'research.errors.timeout',
    KAIROS_RATE_LIMITED: 'research.errors.rateLimited',
    KAIROS_INVALID_KEY: 'research.errors.invalidKey',
    SESSION_NOT_FOUND: 'research.errors.sessionNotFound',
    SEED_TOO_SHORT: 'research.errors.seedTooShort',
    SEED_TOO_LONG: 'research.errors.seedTooLong',
    // US-B04.3 — auth refresh tenté + échoué (frontend-only)
    SESSION_EXPIRED: 'research.errors.sessionExpired',
    // Pas de session_id retourné par /from-seed
    NO_SESSION_ID: 'research.errors.generic',
  }
  return map[code] || 'research.errors.generic'
}
