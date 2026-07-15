# Brique E2E "round-trip email" (magic link) — conception

Date : 2026-07-15. Fait suite au Lot B compte-client (`docs/superpowers/specs/2026-07-14-compte-client-design.md`),
dont l'alerte de clôture signalait : « round-trip email E2E non testé, ASSUMÉ IMPOSSIBLE avec
l'infra actuelle ». Ce document referme ce gap.

## Contexte

`ensure_client_account()` (`backend/app/services/client_account_service.py`) envoie un magic
link Supabase par email (via Resend) lors de la création d'un compte client, déclenché par deux
circuits : réservation Cal.com confirmée, ou devis marqué "payé" en admin. Aucun test E2E
existant ne vérifie la réception réelle de cet email ni le clic sur le lien — les fixtures
`frontend/tests/e2e/fixtures/auth.ts` injectent une session directement en localStorage, sans
jamais passer par un vrai flux email.

**Décision Amine (2026-07-15)** : construire cette brique plutôt que documenter le gap comme
accepté. Vendor de lecture d'email : réutiliser l'infra Google Workspace `afriquestrategie.com`
déjà administrée (GAM7, compte de service à délégation domaine — DWD), pas de nouveau service
payant type Mailosaur.

## Vérifications système faites avant conception (pas de suppositions)

- Scope Gmail déjà autorisé sur le compte de service DWD `gam-project-ip0f8@gam-project-ip0f8
  .iam.gserviceaccount.com` — testé en lecture seule sur `a.mansouri@afriquestrategie.com`
  (`gam.exe user ... show messages maxtoshow 1`), fonctionne sans nouvelle demande d'accès
  Google.
- `RESEND_API_KEY` bien présente sur le conteneur prod live (vérifié par `docker exec ... env`,
  noms de variables seulement) — `docs/05-integrations.md` affirmait à tort le contraire
  (US-204 marqué bloquant alors que `passes=true` depuis le 2026-07-09) ; doc à corriger dans
  le même chantier.
- `ensure_client_account()` n'envoie l'email **que** lors de la création initiale
  (`client_account_service.py:202-214` — retour idempotent silencieux si l'utilisateur existe
  déjà, sans renvoyer de lien). Réutiliser tel quel `a.mansouri@afriquestrategie.com` casserait
  le test dès la 2ᵉ exécution.
- Le super-admin réel de Bassira est `medamine.mansouriidrissi@gmail.com` (constante
  `SUPER_ADMIN_EMAIL`, `frontend/tests/e2e/fixtures/auth.ts`) — mailbox personnelle, hors
  contrôle Workspace/GAM. `a.mansouri@afriquestrategie.com` n'a donc pas besoin de droits admin
  Bassira : il sert uniquement de destinataire de test.
- Mot de passe réel de `medamine.mansouriidrissi@gmail.com` ajouté au coffre DPAPI sous
  `BASSIRA_ADMIN_PASSWORD` (SOP-001, barrière 5, `add-secret.ps1`) — connexion réelle testée et
  confirmée contre `https://prospectives.ai-mpower.com/login` (test jetable, supprimé après
  succès).
- `POST /api/quotes` (création de devis) est un endpoint public (`backend/app/api/quote.py:50`),
  sans authentification requise — utilisable directement sans repasser par la conversation
  agent d'intake (déjà couverte par les tests d'intake existants).

## Architecture

Aucun code backend nouveau : la brique n'exerce que des chemins déjà en production. Deux
nouveaux fichiers front :

- `frontend/tests/e2e/fixtures/gmail-reader.ts` — encapsule toute la lecture Gmail. Expose
  `waitForEmail({ subjectContains, toAddress, timeoutMs })` → corps HTML du message trouvé, et
  `trashMessage(id)`. Authentification via `googleapis` (nouvelle devDependency — client
  officiel Google, seul ajout de dépendance de ce chantier) avec le compte de service existant
  (`C:\Users\amans\.gam\oauth2service.json`, chemin fourni par variable d'environnement locale,
  non committée), en impersonation JWT de `a.mansouri@afriquestrategie.com`.
- `frontend/tests/e2e/client-account-email-roundtrip.spec.ts` — orchestre le scénario complet
  (voir Flux ci-dessous).

## Flux du test

1. Génère un tag unique par run : `a.mansouri+e2e-${crypto.randomUUID()}@afriquestrategie.com`.
   Garantit un `ensure_client_account` non-idempotent (donc un envoi d'email réel) à chaque
   exécution, sans jamais nettoyer Supabase entre les runs.
2. `POST /api/quotes` avec `customer_email` = l'adresse taguée — crée un devis minimal réel.
3. Connexion réelle super-admin (`medamine.mansouriidrissi@gmail.com` /
   `process.env.BASSIRA_ADMIN_PASSWORD`, jamais loggé) via `/login`.
4. Dans `/admin/quotes`, marque ce devis "payé" via l'action UI réelle → déclenche
   `update_quote_status` → `ensure_client_account(source="quote_paid")` → email réel envoyé par
   Resend.
5. `gmailReader.waitForEmail(...)` — poll à intervalle court jusqu'à réception (timeout ~30s),
   extraction du `magic_link` du corps HTML par regex.
6. **Nouveau contexte navigateur** (pas la session admin, pour éviter toute contamination de
   session) → navigue sur le magic link → assert atterrissage sur `/client/dashboard`, session
   active (élément caractéristique du dashboard visible).
7. Nettoyage : `trashMessage` sur l'email lu. Pas de suppression Supabase dans le chemin chaud
   du test (comptes `+e2e-*` reconnaissables par leur pattern d'email — purge différée,
   éventuellement via un script manuel séparé, hors scope de ce chantier).

## Gestion d'erreurs

Si aucun email ne survient dans le timeout → échec de test explicite avec message clair
(« email de compte client non reçu dans le délai imparti »), jamais de skip silencieux : c'était
précisément le trou de couverture identifié à combler, un échec ici doit rester visible.

## Tests

La brique est elle-même un test E2E. Aucun test unitaire supplémentaire nécessaire —
`client_account_service.py` est déjà couvert à 9/9 côté unitaire (Lot B, US-B1).

## Risque non encore validé (à vérifier en premier dans le plan)

L'accès Gmail en lecture via DWD a été prouvé sur `a.mansouri@afriquestrategie.com` telle
quelle — **pas encore prouvé pour une adresse taguée `+e2e-...`**. L'adressage `+tag` est un
comportement Gmail standard (le message atterrit dans la boîte de base), mais ce n'est pas
vérifié pour ce domaine Workspace précis. Doit être la toute première tâche du plan
d'implémentation (spike de preuve, avant d'écrire le reste de la brique) — si le `+tag` ne
fonctionne pas, repli immédiat sur un filtre Gmail par sujet + destinataire de base sans tag.

## Hors scope (explicitement)

- Pas de nettoyage automatique des comptes Supabase `+e2e-*` dans le test lui-même (risque
  disproportionné pour un chemin chaud exécuté à chaque run — clé service-role dans les tests).
- Pas de test du circuit Cal.com (réservation) pour ce round-trip — le circuit "devis payé" est
  suffisant pour valider le mécanisme d'email générique, les deux circuits appellent la même
  `ensure_client_account()`.
- Correction de `docs/05-integrations.md` (RESEND_API_KEY) : à faire dans le même commit que
  l'implémentation, pas un chantier séparé.
