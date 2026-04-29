/**
 * Frontend helper to convert a backend API error into a localised, user-facing
 * message via vue-i18n.
 *
 * The backend (US-007) now returns errors with the shape:
 *   { success: false, error_code: 'SCREAMING_SNAKE_CASE', error: 'fallback en' }
 *
 * `error_code` keys are mapped to translation keys under `errors.*` in
 * `src/locales/{fr,en,ar}.json`. When the code is missing or absent from the
 * locale file, the function falls back gracefully on the raw `error` string
 * (or the JS Error message), so a user never sees a blank toast.
 *
 * @example
 *   import { formatApiError } from '@/utils/error-handler'
 *   import { useI18n } from 'vue-i18n'
 *   const { t } = useI18n()
 *   try { await api.post(...) }
 *   catch (err) { showToast(formatApiError(err, t)) }
 *
 * @param {unknown} error
 *   Either an axios error (with `error.response.data.{error,error_code}`),
 *   a structured backend payload `{ success, error, error_code }`,
 *   or a plain `Error` object.
 * @param {(key: string, params?: object) => string} t
 *   The i18n translation function — typically obtained via `useI18n()`.
 * @returns {string} A localised, user-facing error message.
 */
export function formatApiError(error, t) {
  // Defensive: t is required. If absent, degrade gracefully and still
  // return the best raw message we can find.
  const safeT = typeof t === 'function' ? t : (key) => key

  // Axios error: structured payload lives under error.response.data.
  // Standalone backend payload: keys are at the top level.
  // Plain Error: fallback to .message at the very end.
  const payload =
    (error && typeof error === 'object' && error.response && error.response.data) ||
    (error && typeof error === 'object' ? error : null)

  const errorCode = payload && typeof payload.error_code === 'string' ? payload.error_code : null
  const rawMessage =
    (payload && typeof payload.error === 'string' && payload.error) ||
    (error && typeof error === 'object' && typeof error.message === 'string' && error.message) ||
    ''

  if (errorCode) {
    const localeKey = `errors.${errorCode}`
    const translated = safeT(localeKey)
    // vue-i18n returns the key itself when the translation is missing —
    // in that case fall back to the raw English message rather than
    // showing the SCREAMING_SNAKE_CASE token to the user.
    if (translated && translated !== localeKey) {
      return translated
    }
    if (rawMessage) return rawMessage
    return safeT('errors.UNKNOWN')
  }

  if (rawMessage) return rawMessage

  return safeT('errors.UNKNOWN')
}
