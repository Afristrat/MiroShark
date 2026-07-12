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

/**
 * Un tour de l'agent conversationnel de qualification (étape B, US-IQ-02).
 *
 * @param {string} sessionId
 * @param {string} message — texte du décideur (non vide, y compris l'amorce
 *   synthétique du montage de IntakeAgentPanel.vue)
 * @returns {Promise<{success:true, data:{session_id, state, agent_turns,
 *   message, close, confidential_flags, route?, calcom_link?,
 *   package_recommendation?}}>}
 */
export const postAgentTurn = (sessionId, message) => {
  return service.post(`/api/intake/session/${sessionId}/agent/turn`, { message })
}

/**
 * Clôture directement la session sans passer par le chat (bouton
 * « Passer cette étape », US-IQ-02 frontend).
 *
 * @param {string} sessionId
 * @returns {Promise<{success:true, data:{session_id, state, route,
 *   calcom_link?, package_recommendation?}}>}
 */
export const completeIntakeSession = (sessionId) => {
  return service.post(`/api/intake/session/${sessionId}/complete`, {})
}
