/**
 * Bassira — Supabase client singleton (US-093)
 * ─────────────────────────────────────────────────────────────────────
 * Client JS Supabase configuré avec la clé publique « anon ». Cette
 * clé est SAFE en bundle frontend : elle ne donne accès qu'aux données
 * autorisées par les policies RLS (cf. migration 001 multitenant).
 *
 * Variables d'environnement Vite (lues au build) :
 *   - VITE_SUPABASE_URL       : ex. https://abcdefg.supabase.co
 *   - VITE_SUPABASE_ANON_KEY  : JWT public Supabase
 *
 * Au build local sans Supabase live, des placeholders suffisent — le
 * client se construit, et toute requête échoue gracieusement avec une
 * erreur réseau qui sera capturée par l'UI. La vraie validation se
 * fait au déploiement Coolify où les vraies vars sont posées.
 */

import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co'
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJ.placeholder'

export const supabase = createClient(url, anonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storageKey: 'bassira_supabase_auth'
  }
})

/**
 * Indique si la configuration Supabase utilise les placeholders de build.
 * Permet à l'UI d'afficher un message explicite au lieu d'échouer
 * silencieusement quand la prod n'a pas encore les variables posées.
 */
export const isSupabasePlaceholder =
  url === 'https://placeholder.supabase.co' || anonKey === 'eyJ.placeholder'
