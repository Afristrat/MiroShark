/**
 * Bassira — Auth store Pinia (US-093)
 * ─────────────────────────────────────────────────────────────────────
 * Gère l'état d'authentification Supabase + le profil multitenant
 * (organizations + rôle). La session est persistée par Supabase lui-même
 * dans localStorage (storageKey 'bassira_supabase_auth') ; init() la
 * recharge au démarrage de l'app.
 *
 * Contrat /api/auth/me (US-092) attendu :
 *   {
 *     user_id: "uuid",
 *     email: "user@example.com",
 *     orgs: [
 *       { id: "uuid", name: "ACME", slug: "acme", role: "owner" },
 *       { id: "uuid", name: "Other", slug: "other", role: "viewer" }
 *     ]
 *   }
 */

import { defineStore } from 'pinia'
import { supabase } from '../lib/supabase'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,           // Supabase auth User | null
    session: null,        // Supabase Session | null
    orgs: [],             // [{ id, name, slug, role }]
    currentOrgId: null,   // string | null
    profileLoaded: false, // true après un fetchProfile() réussi
    initializing: true,   // true tant que la 1ère récupération de session n'est pas faite
    error: null           // dernier message d'erreur (login/signup/fetchProfile)
  }),

  getters: {
    isAuthenticated(state) {
      return !!state.session && !!state.user
    },
    currentOrg(state) {
      if (!state.currentOrgId) return null
      return state.orgs.find((o) => o.id === state.currentOrgId) || null
    },
    currentRole() {
      const org = this.currentOrg
      return org ? org.role : null
    },
    /**
     * true si le rôle courant peut écrire (marquer outcome, publier).
     * Hiérarchie : owner > admin > member > viewer.
     */
    canWrite() {
      const role = this.currentRole
      return role === 'owner' || role === 'admin'
    }
  },

  actions: {
    /**
     * Initialise le store au démarrage de l'app : récupère la session
     * Supabase persistée et abonne aux changements d'auth.
     */
    async init() {
      try {
        const { data, error } = await supabase.auth.getSession()
        if (error) {
          // Erreur réseau ou Supabase down — on log mais on n'empêche
          // pas l'app de tourner (les routes publiques restent accessibles).
          console.warn('[Bassira auth] init getSession failed:', error.message)
        }
        this.session = data?.session || null
        this.user = data?.session?.user || null

        // Listener : tout changement d'état auth (login, logout, refresh)
        // met à jour le store. Pinia est réactif → la nav réagit auto.
        supabase.auth.onAuthStateChange((event, session) => {
          this.session = session || null
          this.user = session?.user || null
          if (event === 'SIGNED_OUT') {
            this.orgs = []
            this.currentOrgId = null
            this.profileLoaded = false
          }
        })

        // Si déjà connecté au boot, on charge le profil silencieusement.
        if (this.isAuthenticated && !this.profileLoaded) {
          this.fetchProfile().catch(() => {
            // Erreur silencieuse — la dashboard view re-tentera et
            // affichera le message d'erreur à l'utilisateur.
          })
        }
      } finally {
        this.initializing = false
      }
    },

    /**
     * Connexion email + mot de passe.
     * @returns {Promise<{ error: string|null }>}
     */
    async login(email, password) {
      this.error = null
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
      })
      if (error) {
        this.error = error.message
        return { error: error.message }
      }
      this.session = data.session
      this.user = data.user
      // Charge le profil multitenant. Si l'endpoint /api/auth/me n'est
      // pas encore déployé (US-092 pas mergé), on log mais on continue —
      // l'utilisateur sera redirigé vers le dashboard qui affichera
      // un message « En attente d'invitation ».
      try {
        await this.fetchProfile()
      } catch (err) {
        console.warn('[Bassira auth] fetchProfile after login failed:', err.message)
      }
      return { error: null }
    },

    /**
     * Inscription. Crée juste le user Supabase Auth ; l'attribution à
     * une organisation est faite manuellement par l'équipe Bassira en
     * SQL Editor pour les premiers clients (cf. supabase/seed.sql).
     * @returns {Promise<{ error: string|null, needsConfirmation: boolean }>}
     */
    async signup(email, password, metadata = {}) {
      this.error = null
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: metadata // full_name, organization_name (utilisés par l'équipe pour créer l'org)
        }
      })
      if (error) {
        this.error = error.message
        return { error: error.message, needsConfirmation: false }
      }
      // Selon la config Supabase, soit la session est créée immédiatement,
      // soit l'utilisateur doit confirmer son email d'abord.
      const needsConfirmation = !data.session
      if (data.session) {
        this.session = data.session
        this.user = data.user
      }
      return { error: null, needsConfirmation }
    },

    /**
     * Déconnexion. Supabase invalide la session côté serveur et
     * efface les tokens du localStorage.
     */
    async logout() {
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.warn('[Bassira auth] signOut error:', error.message)
      }
      this.user = null
      this.session = null
      this.orgs = []
      this.currentOrgId = null
      this.profileLoaded = false
      this.error = null
    },

    /**
     * Récupère le profil multitenant depuis le backend (US-092).
     * Appelle GET /api/auth/me avec le bearer token. Le résultat
     * peuple `orgs` et sélectionne `currentOrgId` (1ère org par défaut).
     */
    async fetchProfile() {
      if (!this.session?.access_token) {
        throw new Error('Aucune session active')
      }
      const res = await fetch('/api/auth/me', {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${this.session.access_token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(`fetchProfile ${res.status}: ${text || res.statusText}`)
      }
      const data = await res.json()
      // Tolérant : accepte soit { orgs: [...] } soit { data: { orgs: [...] } }
      const payload = data?.data || data
      this.orgs = Array.isArray(payload?.orgs) ? payload.orgs : []
      // Conserve l'org courante si toujours valide, sinon prend la 1ère.
      if (
        this.currentOrgId &&
        this.orgs.some((o) => o.id === this.currentOrgId)
      ) {
        // ok, on garde
      } else {
        this.currentOrgId = this.orgs[0]?.id || null
      }
      this.profileLoaded = true
      return this.orgs
    },

    /**
     * Sélectionne une org parmi celles disponibles.
     */
    setCurrentOrg(orgId) {
      if (this.orgs.some((o) => o.id === orgId)) {
        this.currentOrgId = orgId
      }
    }
  }
})
