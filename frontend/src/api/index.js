import axios from 'axios'
import i18nInstance from '../i18n'
import { useAuthStore } from '../stores/auth'
import { supabase } from '../lib/supabase'

// Create axios instance
//
// baseURL must remain RELATIVE ('') in prod so axios calls /api/* via the
// reverse-proxy (Cloudflare tunnel → Traefik → vite preview → Flask backend).
// The fallback 'http://localhost:5001' came from the upstream MiroShark fork
// and broke the prod build : the bundled JS sent to the browser tried to fetch
// localhost:5001 from the user's own machine (not the container), returning
// 503 « Network error » on every API call. Setting baseURL='' lets axios fire
// same-origin /api/* requests which the reverse-proxy routes correctly in
// dev (vite dev `server.proxy`) and in prod (vite preview `preview.proxy`).
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 300000, // 5-minute timeout (ontology generation may take a long time)
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
service.interceptors.request.use(
  async config => {
    // US-043 — propage la locale UI courante au backend pour que les
    // system prompts LLM (ontology, agents, rapport) répondent dans la
    // langue de l'utilisateur (cf backend/app/utils/locale_prompt.py).
    try {
      const locale = i18nInstance.global?.locale?.value || 'fr'
      config.headers = config.headers || {}
      config.headers['X-Bassira-Locale'] = locale
    } catch (_) {
      // i18n pas encore initialisé (rarissime au boot) → backend default 'fr'
    }
    // Admin token (opérateur uniquement) — stocké dans sessionStorage.
    // Auto-attaché aux endpoints qui en ont besoin :
    //   - POST /api/simulation/<id>/outcome (US-020 publish/resolve)
    //   - GET  /api/admin/* (US-065 dashboard analytics)
    const isAdminRequest = config.url && (
      config.url.includes('/outcome') || config.url.includes('/admin')
    )
    const adminToken = sessionStorage.getItem('bassira_admin_token')
    if (adminToken && isAdminRequest) {
      config.headers['Authorization'] = `Bearer ${adminToken}`
    } else {
      let token = null
      try {
        const auth = useAuthStore()
        token = auth.session?.access_token || null
        if (auth.currentOrgId) config.headers['X-Org-Id'] = auth.currentOrgId
      } catch (_) {
        // Pinia may not be ready during bootstrap; Supabase remains the source of truth.
      }
      if (!token) {
        try {
          const { data } = await supabase.auth.getSession()
          token = data.session?.access_token || null
        } catch (_) {
          // The protected endpoint will return 401 if the local session cannot be read.
        }
      }
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`
      }
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor (fault-tolerant retry mechanism)
service.interceptors.response.use(
  response => {
    const res = response.data
    
    // If the returned status is not success, throw an error
    if (!res.success && res.success !== undefined) {
      console.error('API Error:', res.error || res.message || 'Unknown error')
      return Promise.reject(new Error(res.error || res.message || 'Error'))
    }
    
    return res
  },
  error => {
    console.error('Response error:', error)
    
    // Handle timeout
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      console.error('Request timeout')
    }
    
    // Handle network error
    if (error.message === 'Network Error') {
      console.error('Network error - please check your connection')
    }
    
    return Promise.reject(error)
  }
)

// Request function with retry
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn()
    } catch (error) {
      if (i === maxRetries - 1) throw error
      
      console.warn(`Request failed, retrying (${i + 1}/${maxRetries})...`)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}

export default service
