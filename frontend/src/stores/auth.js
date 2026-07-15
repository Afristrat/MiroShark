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

// Mémoïsation de init() en dehors du store (module-scope, un seul store
// auth dans l'app) — cf. US-093-bis. Le routeur (beforeEach) démarre sa
// résolution de navigation initiale AVANT que main.js n'ait fini
// d'attendre init() (Vue Router n'est pas gaté par app.mount()) : sans
// cette mémoïsation, un guard qui se déclenche pendant l'attente de
// init() lit un store encore à l'état par défaut (isAuthenticated=false)
// et redirige vers /login avant même que la session issue d'un magic
// link n'ait fini de s'écrire. Tout appelant (main.js, le guard) attend
// la même promesse plutôt que de relire un état pas encore prêt.
let initPromise = null

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,           // Supabase auth User | null
    session: null,        // Supabase Session | null
    orgs: [],             // [{ id, name, slug, role }]
    currentOrgId: null,   // string | null
    profileLoaded: false, // true après un fetchProfile() réussi
    initializing: true,   // true tant que la 1ère récupération de session n'est pas faite
    error: null,          // dernier message d'erreur (login/signup/fetchProfile)
    // US-095 — flag super-admin Bassira (founders only). Chargé via
    // fetchSuperStatus() après login. Reste null tant que la requête
    // n'a pas répondu (permet au frontend de distinguer « pas chargé »
    // de « définitivement false »).
    superAdminLoaded: false,
    isSuperAdminFlag: false
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
    },
    /**
     * US-095 — true si l'user est super-admin Bassira (whitelist email
     * côté backend). Toujours false tant que fetchSuperStatus() n'a pas
     * répondu — la décision d'autorisation reste côté serveur.
     */
    isSuperAdmin(state) {
      return Boolean(state.isSuperAdminFlag)
    }
  },

  actions: {
    /**
     * Initialise le store au démarrage de l'app : récupère la session
     * Supabase persistée et abonne aux changements d'auth.
     *
     * Mémoïsé (cf. `initPromise` module-scope) — le routeur (beforeEach)
     * et main.js peuvent tous deux appeler init() ; le second attend
     * simplement la promesse déjà en cours plutôt que d'agir sur un état
     * pas encore prêt.
     */
    init() {
      if (!initPromise) {
        initPromise = this._runInit()
      }
      return initPromise
    },

    async _runInit() {
      try {
        // US-096 fix — Si on revient d'un OAuth implicit (Google) ou d'un
        // magic link, l'URL contient un fragment `#access_token=...` que
        // Supabase JS doit d'abord parser via detectSessionInUrl AVANT que
        // getSession() ne renvoie une session valide. On attend l'event
        // SIGNED_IN (failsafe 3s).
        if (typeof window !== 'undefined' && window.location.hash.includes('access_token=')) {
          await new Promise((resolve) => {
            let done = false
            const finish = () => { if (!done) { done = true; resolve() } }
            const { data: sub } = supabase.auth.onAuthStateChange((event) => {
              if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
                try { sub?.subscription?.unsubscribe?.() } catch (_) { /* ignore */ }
                finish()
              }
            })
            setTimeout(finish, 3000)
          })
        }

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
            // US-095 — purge le flag super-admin au sign-out
            this.isSuperAdminFlag = false
            this.superAdminLoaded = false
          }
        })

        // Si déjà connecté au boot, on charge le profil silencieusement.
        if (this.isAuthenticated && !this.profileLoaded) {
          this.fetchProfile().catch(() => {
            // Erreur silencieuse — la dashboard view re-tentera et
            // affichera le message d'erreur à l'utilisateur.
          })
          // US-095 — charge aussi le flag super-admin au boot
          this.fetchSuperStatus().catch(() => {
            /* fail-soft : false par défaut */
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
      // US-095 — charge le flag super-admin (parallèle au profil mais
      // sans bloquer la promesse de login en cas d'échec).
      try {
        await this.fetchSuperStatus()
      } catch (err) {
        console.warn('[Bassira auth] fetchSuperStatus after login failed:', err.message)
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
      // US-095 — purge le flag super-admin
      this.isSuperAdminFlag = false
      this.superAdminLoaded = false
    },

    /**
     * Récupère le profil multitenant depuis le backend (US-092).
     * Appelle GET /api/client/auth/me avec le bearer token. Le résultat
     * peuple `orgs` et sélectionne `currentOrgId` (1ère org par défaut).
     *
     * IMPORTANT : le path est /api/client/auth/me (pas /api/auth/me) — le
     * blueprint backend client_bp est monté au préfixe /api/client/.
     */
    async fetchProfile() {
      if (!this.session?.access_token) {
        throw new Error('Aucune session active')
      }
      const res = await fetch('/api/client/auth/me', {
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
    },

    /**
     * US-095 — Récupère le flag super-admin depuis le backend.
     * Réinitialise à false en cas d'erreur (zero-trust côté frontend).
     * À appeler après init() / login() / fetchProfile() — la décision
     * d'autorisation reste 100 % côté serveur (whitelist email env var).
     */
    async fetchSuperStatus() {
      if (!this.session?.access_token) {
        this.isSuperAdminFlag = false
        this.superAdminLoaded = false
        return false
      }
      try {
        const res = await fetch('/api/admin/me/super-status', {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${this.session.access_token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin'
        })
        if (!res.ok) {
          // 401 / 5xx — on retombe à false plutôt que de fail bruyamment.
          // Le backend reste seul juge ; le frontend ne fait que cacher
          // l'entrée nav s'il ne peut pas confirmer le flag.
          this.isSuperAdminFlag = false
          this.superAdminLoaded = true
          return false
        }
        const data = await res.json()
        const payload = data?.data || data
        this.isSuperAdminFlag = Boolean(payload?.is_super_admin)
        this.superAdminLoaded = true
        return this.isSuperAdminFlag
      } catch (err) {
        // Réseau down → false par défaut, on retentera au prochain login.
        console.warn('[Bassira auth] fetchSuperStatus failed:', err.message)
        this.isSuperAdminFlag = false
        this.superAdminLoaded = false
        return false
      }
    }
  }
})
