import service from './index'

/**
 * Submit a quote-request payload from the /devis form (US-025).
 *
 * @param {Object} payload — every required field below + optional ones.
 * @param {string} payload.full_name        — required, ≤ 100 chars
 * @param {string} payload.email            — required, validated format
 * @param {string} payload.company          — required, ≤ 120 chars
 * @param {string} [payload.role]           — optional, ≤ 80 chars
 * @param {string} [payload.phone]          — optional
 * @param {string} payload.package          — required, one of
 *   `crisis_drill_24h` | `policy_brief_stress` | `pre_launch_adcheck` | `custom`
 * @param {number} [payload.expected_simulations_per_year] — 1..100
 * @param {string} [payload.target_deadline] — `not_urgent` | `1_month` | `2_weeks` | `this_week`
 * @param {string} [payload.industry]
 * @param {string[]} [payload.geo_focus]    — subset of MA/DZ/TN/SN/CI/Other
 * @param {string} [payload.message]        — ≤ 800 chars
 * @param {boolean} payload.consent_rgpd    — must be true
 * @param {string} [payload.locale]         — fr | en | ar (used for email body framing)
 *
 * @returns {Promise<{success:true, data:{quote_id:string, submitted_at:string}}>}
 *
 * Errors are propagated via the shared axios interceptor — backend
 * returns `{success:false, error_code, error}` which `formatApiError`
 * (US-007) localises into a user-facing toast.
 */
export const submitQuote = (payload) => {
  return service.post('/api/quote', payload)
}
