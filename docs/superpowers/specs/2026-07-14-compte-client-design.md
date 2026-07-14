# Design — Lot B : compte client multi-tenant (Bassira)

**Date** : 2026-07-14 · **Statut** : validé par Amine (brainstorming en session, compagnon visuel) ·
**Périmètre** : 2ᵉ des 4 lots du chantier compte-client (A→B→C→D). Lot A (notif admin →
lien fiche demande) déjà livré et déployé (`3517c52`, ADR-IQ-15). Lots C (Cal.com
embarqué) et D (white-label Cal.com) hors scope de ce document.

## 1. Contexte et problème

Aujourd'hui, **aucun compte client n'est créé automatiquement nulle part** dans Bassira :
- Ni par la soumission `/devis` (US-025).
- Ni par le paiement Stripe self-service (`checkout.session.completed`, US-205) — ce
  circuit est **volontairement sans compte** pour préserver la friction minimale à
  l'achat (documenté dans `stripe_checkout.py`).
- Les seuls comptes existants viennent de l'invitation admin manuelle (`invitations.py`,
  US-115).

Le job du compte client est un **portail complet** : statut de la demande, devis,
livrables, gestion de l'organisation. La création du compte doit avoir lieu **à
l'engagement réel du client** (réservation d'un créneau Cal.com, ou paiement d'un devis
via le circuit manuel admin), **jamais à la simple soumission du formulaire** — ceci
préserve la friction minimale actée en ADR-IQ-01.

## 2. Architecture — vue d'ensemble

```
┌─────────────────────┐     ┌─────────────────────┐
│ confirm_calcom_      │     │ update_quote_status  │
│ booking()             │     │ (new_status="paid")   │
│ (intake_service.py)   │     │ (quote_admin_service)│
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           │   circuit devis manuel     │  Stripe Payment Link envoyé
           │   uniquement (jamais le    │  hors self-service, OU
           │   webhook self-service)    │  virement bancaire confirmé
           └─────────────┬──────────────┘
                          ▼
              ┌────────────────────────┐
              │ ensure_client_account()  │
              │ (nouveau — idempotent)   │
              └────────────┬─────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                    ▼
  auth.users          organizations         org_members
  (email_confirm=      (status='trial')      (role='owner')
   False, magic
   link envoyé)
                            │
                            ▼
              re-rattachement quote_ownership
              (org Bassira fallback → org client,
               filtré par customer_email)
```

**Ce qui NE change PAS** : le webhook Stripe self-service (`stripe_checkout.py`,
`checkout.session.completed`, palier d'entrée US-205) **n'appelle jamais**
`ensure_client_account`. L'achat self-service reste explicitement sans compte —
ADR-007/US-205 préservé sans régression.

## 3. `ensure_client_account()` — contrat

```python
def ensure_client_account(
    email: str,
    full_name: str,
    org_name: Optional[str],
    *,
    source: Literal["calcom_booking", "quote_paid"],
    client: Any,
) -> Dict[str, Any]:
    """Retourne {"org_id": uuid, "user_id": uuid, "created": bool}."""
```

**Comportement idempotent** — clé de dédup = **email** (un email qui revient retrouve
son org existante) :

1. Cherche un `auth.users` existant par email (Supabase admin API). Si trouvé et déjà
   membre d'une org (`org_members`) → retourne l'org existante, `created=False`, ne
   recrée rien, n'envoie pas de nouveau magic link.
2. Sinon, crée dans une transaction logique (best-effort, chaque étape loggée) :
   - `auth.users` via l'API admin Supabase (`email_confirm=False`) ;
   - `organizations` (`status='trial'`, `slug` dérivé de `org_name` (slugify) ou de la
     partie locale de l'email si `org_name` absent ; en cas de collision sur la
     contrainte `unique` existante, suffixe un court hash aléatoire (4 caractères) et
     retente une fois) ;
   - `org_members` (`role='owner'`, `invited_by=NULL` — création directe, pas via le
     flux d'invitation) ;
3. Re-rattache les lignes `quote_ownership` existantes (org de repli Bassira,
   `_FALLBACK_ORG_SLUG`) vers la nouvelle org, filtrées par `customer_email = email`.
4. Envoie un magic link Supabase (`signInWithOtp` côté client, déclenché serveur via
   l'API admin) — réutilise le canal email déjà en place pour `org_invitations`.

**Erreurs** : chaque étape est best-effort et loggée (`logger.error`, classe
d'exception seulement — pas de PII en clair dans les logs) ; ne doit **jamais** faire
échouer `confirm_calcom_booking` ni `update_quote_status` — cohérent avec le pattern
déjà en place pour `_send_admin_notification` (ADR-IQ-14).

## 4. Déclencheurs

| Déclencheur | Fichier | Condition |
|---|---|---|
| Réservation Cal.com | `intake_service.py::confirm_calcom_booking()` | Branche `meeting`, après confirmation effective du booking |
| Devis payé (circuit manuel) | `quote_admin_service.py::update_quote_status()` | `new_status == "paid"` — **uniquement** ce point d'entrée admin. Couvre Payment Link Stripe envoyé hors self-service ET virement bancaire confirmé hors-ligne (les deux transitent par cette même fonction, peu importe le moyen de paiement réel) |
| Paiement Stripe self-service | `stripe_checkout.py` (webhook `checkout.session.completed`) | **Explicitement exclu.** Aucun appel à `ensure_client_account`. |

## 5. Portail front

**Réutilisation intégrale de l'infrastructure existante** (aucune création) :
- `/login` — `LoginView.vue` : magic link (`signInWithOtp`, US-096) + mot de passe.
- `/signup` — `SignupView.vue` : signup autonome, état "en attente d'invitation" si pas
  d'org.
- `/client/dashboard` — `ClientDashboardView.vue` : sélecteur multi-org, stats
  simulation (total/published/brierAvg), bannière "pas encore d'org".

**Ajout unique — section "Mes demandes"** (maquette validée en session via compagnon
visuel, `.superpowers/brainstorm/51331-1784056764/content/dashboard-mes-demandes.html`) :
insérée sous les stats existantes dans `ClientDashboardView.vue`. Chaque devis affiche
un label de statut traduit (pas la valeur SQL brute) et un CTA conditionnel (rapport
livré → lien direct ; sinon → détails). i18n polyglotte obligatoire (fr/en/ar) sur tous
les labels de statut.

**Nouvel endpoint backend** — `GET /api/client/quotes` : `require_auth` + résolution
d'org via le pattern déjà utilisé par `invitations.py::_resolve_target_org_for_invite`
(super-admin doit fournir `org_id`, membre normal résout son org automatiquement).
Retourne les lignes `quote_ownership` de l'org courante (payload allégé : quote_id,
package_id, status, created_at — pas le payload PII complet).

## 6. Sécurité / RLS

**Aucune nouvelle policy SQL requise.** La policy `members_can_read_org_quotes`
(migration `20260505_001`, `org_id IN user_orgs()`) couvre déjà la lecture. Puisque
`ensure_client_account` re-rattache `quote_ownership.org_id` vers la nouvelle org du
client, la visibilité est automatique dès que le compte existe.

Point à vérifier **hors scope de ce lot** (mentionné pour mémoire, pas bloquant) : accès
aux livrables (`report_deliveries`/`report_versions`, rattachés via
`simulation_ownership.org_id`) — même famille de pattern RLS attendue, à confirmer au
moment de designer cette section du dashboard (probablement Lot B-bis ou V2).

## 7. Découpage en User Stories

| # | Story | Contenu | Dépend de |
|---|---|---|---|
| US-B1 | `ensure_client_account()` backend | Fonction idempotente complète (§3). Tests unitaires : idempotence sur email existant, race sur email concurrent, échec best-effort n'interrompt pas l'appelant. | — |
| US-B2 | Déclencheur booking Cal.com | Appel dans `confirm_calcom_booking()` (branche `meeting`). | US-B1 |
| US-B3 | Déclencheur devis payé | Appel dans `update_quote_status(new_status="paid")`, circuit admin manuel uniquement. | US-B1 |
| US-B4 | Endpoint `GET /api/client/quotes` | Route + tests (org isolation — un membre d'une org ne voit jamais les devis d'une autre). | US-B1 |
| US-B5 | Section "Mes demandes" front | `ClientDashboardView.vue`, mapping statuts SQL → labels fr/en/ar, CTA conditionnel. | US-B4 |
| US-B6 | Tests E2E Playwright | Parcours réel : booking Cal.com → magic link → login → dashboard affiche la demande. Idem circuit devis payé admin. | US-B2, US-B3, US-B5 |

**Hors scope explicite** : livrables dans le dashboard (design séparé) ; auth/login/signup
(déjà en prod, aucune story) ; RLS `quote_ownership` (déjà en place, aucune story) ;
Lots C et D (Cal.com embarqué, white-label).

## 8. Tests

- Unitaires backend : `ensure_client_account` (idempotence, dédup email, best-effort),
  `update_quote_status` (déclenchement uniquement sur transition vers `paid`),
  `GET /api/client/quotes` (isolation multi-org).
- E2E Playwright (US-B6) : les deux parcours réels de bout en bout, pas de relais chat
  (cohérent avec la pratique déjà en place pour ADR-IQ-12/13/14/15).

## 9. Notes de session (contexte de décision)

- Amine a explicitement choisi de **ne pas** créer de compte sur le circuit Stripe
  self-service, pour préserver la friction minimale déjà actée (ADR-007/US-205).
- Amine a précisé que le circuit "devis payé" doit couvrir aussi bien un Payment Link
  Stripe envoyé manuellement qu'un virement bancaire confirmé hors-ligne — d'où
  l'ancrage sur `update_quote_status`, indépendant du moyen de paiement réel.
- La section "Mes demandes" a été validée visuellement (compagnon de brainstorming,
  maquette conservée dans `.superpowers/brainstorm/51331-1784056764/`).
