import service from './index'

/**
 * Démarre une session de qualification /devis « 3 temps » (US-IQ-01).
 *
 * @param {Object} [opts]
 * @param {string} [opts.locale] — fr | en | ar
 * @param {string} [opts.entry_door] — 'standard' | 'aar' (porte 2, US-IQ-05)
 * @returns {Promise<{success:true, data:{session_id:string, state:string, locale:string}}>}
 */
export const startIntakeSession = (opts = {}) => {
  return service.post('/api/intake/session', opts)
}

/**
 * Soumet le formulaire A1-A8 (+ identité) d'une session démarrée.
 *
 * @param {string} sessionId
 * @param {Object} payload — identité (full_name, email, company, role?,
 *   phone?, consent_rgpd) + `brief` (schéma docs/intake/02-data-dictionary-delta.md)
 * @returns {Promise<{success:true, data:{session_id, quote_id, state}}>}
 */
export const submitIntakeForm = (sessionId, payload) => {
  return service.post(`/api/intake/session/${sessionId}/form`, payload)
}
