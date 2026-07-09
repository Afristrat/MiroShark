import service from './index'

/**
 * Crée une Checkout Session Stripe pour un package d'entrée en self-service
 * (US-205, ADR-014). Retourne l'URL Stripe hébergée vers laquelle rediriger.
 *
 * @param {Object} params
 * @param {string} params.package_id — un des 3 packages d'entrée
 *   (`pmf_discovery` | `crisis_drill_24h` | `adcheck_lite`)
 * @param {string} params.currency — `mad` | `usd` | `eur`
 * @param {string} [params.customer_email]
 *
 * @returns {Promise<{success:true, data:{checkout_url:string}}>}
 */
export const createCheckoutSession = (params) => {
  return service.post('/api/stripe/create-checkout-session', params)
}
