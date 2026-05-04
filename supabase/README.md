# Supabase — Multitenant Bassira

Procédure step-by-step pour appliquer le schéma multitenant sur la DB Supabase Cloud Bassira. Tout passe par le **dashboard Supabase**, aucune CLI ni machine locale requise.

## Inventaire

| Fichier | Rôle |
|---|---|
| `migrations/20260503_001_init_multitenant.sql` | Tables `organizations` + `org_members` + `simulation_ownership` + indexes + RLS policies + trigger updated_at |
| `migrations/20260503_002_public_calibration_view.sql` | VIEW publique agrégée k-anonymity n≥5 pour `/calibration` v2 |
| `migrations/20260504_001_org_self_service.sql` | Ajoute la colonne `self_service_enabled bool default false` sur `organizations` (US-098) |
| `migrations/20260504_002_backfill_legacy_sims.sql` | Rétro-attribue les sims filesystem pré-multitenant à l'org `aimpower-bassira` (US-101) |
| `seed.sql` | Crée l'org "AIMPOWER" (toi en owner après signup) |

---

## Étape 1 — Exécuter la migration 001

1. Ouvre le **SQL Editor** de ton projet Supabase Bassira :
   - Dashboard → projet Bassira → menu gauche → **SQL Editor** (icône terminal)
2. Clique **+ New query**, colle l'intégralité de `migrations/20260503_001_init_multitenant.sql`, puis **Run** (Ctrl+Enter)
3. Vérifie en bas : « Success. No rows returned » (ou similaire)

**Vérification** dans le **Table Editor** (menu gauche → icône table) :
- Tu dois voir 3 nouvelles tables : `organizations`, `org_members`, `simulation_ownership`
- Sur chaque, l'icône cadenas 🔒 « RLS enabled » doit être présente

---

## Étape 2 — Exécuter la migration 002

Même procédure : nouvelle query, colle `migrations/20260503_002_public_calibration_view.sql`, Run.

**Vérification** : Table Editor → onglet « Views » → `public_calibration_aggregates` doit apparaître (vide pour l'instant, normal — pas encore de sims publiées).

---

## Étape 3 — Exécuter le seed (étape A uniquement)

Nouvelle query, colle `seed.sql` **uniquement la section [A]** (les sections [B] et [C] sont commentées dans le fichier — laisse-les commentées pour l'instant).

**Vérification** : Table Editor → `organizations` → tu dois voir une ligne avec `slug = aimpower-bassira`.

---

## Étape 4 — Créer ton compte (signup) via Supabase Auth

**2 options** :

### Option 4.A — Via le dashboard (rapide pour le MVP)

1. Dashboard → menu gauche → **Authentication** → **Users**
2. Bouton **Add user → Create new user**
3. Email : ton email professionnel · Password : un mot de passe fort · Coche **Auto Confirm User** (sinon il faudra confirmer par mail)
4. Clique **Create user**
5. Dans la liste des users, clique sur ton email → copie le **UID** (format `uuid` du genre `abc12345-...`) → garde-le

### Option 4.B — Via la future page `/login` Bassira (plus tard, après US-093)

Pour l'instant cette page n'existe pas. On l'attendra pour que tu fasses l'inscription depuis l'UI.

---

## Étape 5 — Te poser comme `owner` de l'org AIMPOWER

1. SQL Editor → nouvelle query
2. Colle ce qui suit en **remplaçant `<YOUR_AUTH_USER_ID>`** par l'UID que tu viens de copier :

```sql
insert into public.org_members (org_id, user_id, role)
select o.id, '<YOUR_AUTH_USER_ID>'::uuid, 'owner'
from public.organizations o
where o.slug = 'aimpower-bassira'
on conflict (org_id, user_id) do update set role = 'owner';
```

3. Run

**Vérification** : Table Editor → `org_members` → 1 ligne avec ton `user_id` + role `owner`.

---

## Étape 6 — (Optionnel) Tester les RLS

Toujours dans le SQL Editor, lance ces 3 SELECTs **avec le rôle authenticated** (en haut à droite du SQL Editor il y a un dropdown de rôle, mets **authenticated** + paste un JWT user via le bouton à côté ; ou plus simple : utilise **Auth helpers** de Supabase) :

```sql
-- Doit retourner 1 ligne : ton org AIMPOWER
select * from public.organizations;

-- Doit retourner 1 ligne : ta membership owner
select * from public.org_members;

-- Doit retourner 0 lignes (pas encore de sims attribuées)
select * from public.simulation_ownership;
```

Avec le rôle `anon` (utilisateur non connecté), les 3 mêmes SELECTs doivent retourner **0 lignes** (RLS bloque).

---

## Étape 7 — Confirmer et passer la main

Quand les étapes 1 → 5 sont validées, dis-moi :
- « migrations OK, je suis owner de aimpower-bassira »

Et je pourrai dispatcher US-092 (backend Flask middleware JWT + extension SimulationManager pour ownership) + US-093 (frontend LoginView + AuthStore + route guards).

---

## Notes

- **Pas de migration côté Coolify** à ce stade. Coolify n'a besoin que des 5 env vars Supabase pour le runtime (ce que tu as déjà fait).
- **`seed.sql` peut être ré-exécuté** sans risque (toutes les insertions ont des `on conflict do nothing` ou `do update`).
- **Si tu te trompes** : le SQL Editor permet aussi de `drop table organizations cascade;` pour repartir de zéro. Les migrations sont idempotentes (création des tables avec `if not exists`, etc.) — on peut les rejouer.

---

## Étape 8 — (US-098) Activer le toggle self-service par org

**À jouer après le déploiement US-098** :

1. SQL Editor → nouvelle query → colle l'intégralité de `migrations/20260504_001_org_self_service.sql` → **Run**.
2. Vérification : Table Editor → `organizations` → la colonne `self_service_enabled` (boolean, default false) doit apparaître.
3. Pour activer le self-service sur une org, soit :
   - **Via UI** : `/admin/analytics` → section « Toutes les organisations » → toggle « Self-service activé » sur la ligne de l'org (super-admin only).
   - **Via SQL direct** : `update public.organizations set self_service_enabled = true where slug = 'aimpower-bassira';`

Le flag est lu par le décorateur backend `@require_self_service_enabled` qui retourne 403 `SELF_SERVICE_DISABLED` si l'org n'a pas le drapeau (sauf super-admin).

---

## Étape 9 — (US-101) Rétro-attribution des sims filesystem pré-multitenant

**Quand jouer cette migration** : maintenant, après que US-091 (multitenant) + US-098 (self-service) + US-100 (admin auth) soient en prod et que tu aies vérifié que la vue super-admin `/admin/analytics` affiche bien un total de sims non nul mais un tableau cross-tenant vide (incohérence remontée par Amine, cause : aucune entrée dans `public.simulation_ownership` pour les sims créées avant US-091).

**Bloc unique à jouer une seule fois** :

1. Sur le **serveur prod Coolify** (ou via un snapshot prod copié en local), génère la liste réelle des sims filesystem :

   ```bash
   cd backend && uv run python scripts/check_legacy_sims_attribution.py --sql
   ```

   Cette commande affiche les lignes `VALUES (...)` prêtes à coller, calculées depuis :
   - le nom du dossier (`sim_xxxxxxxxxxxx`) → `simulation_id`
   - le `mtime` du dossier → `created_at` (ISO 8601 UTC)
   - `simulation_config.json` clés `template_id` / `package_id` → `package_id`
   - `outcome.json` (si présent) → `outcome` (jsonb) + `brier_score`

2. Ouvre `supabase/migrations/20260504_002_backfill_legacy_sims.sql`, remplace le bloc placeholder (`'__placeholder__'`) par la sortie du script, sauvegarde.

3. SQL Editor Supabase Bassira → nouvelle query → colle l'intégralité du fichier modifié → **Run**.

   La requête est **idempotente** : `on conflict (simulation_id) do nothing` garantit qu'une nouvelle exécution n'écrase ni ne duplique rien.

**Vérification post-exécution** (queries dans le SQL Editor) :

```sql
-- Doit retourner un nombre = nombre de dossiers sim_* sur la prod
select count(*) as sims_attributed
  from public.simulation_ownership s
  join public.organizations o on o.id = s.org_id
 where o.slug = 'aimpower-bassira';

-- Spot-check des 20 plus récentes
select s.simulation_id, s.created_at, s.package_id, s.is_published
  from public.simulation_ownership s
  join public.organizations o on o.id = s.org_id
 where o.slug = 'aimpower-bassira'
 order by s.created_at desc
 limit 20;
```

Comparer le `count(*)` avec la sortie locale de :
```bash
cd backend && uv run python scripts/check_legacy_sims_attribution.py
```

**Ajouter de nouvelles sims rétroactivement plus tard** : si après cette migration de nouvelles sims orphelines apparaissent (par ex. import depuis un environnement tiers), il suffit de :
1. Relancer le script Python en mode `--sql` pour récupérer uniquement les nouvelles lignes.
2. Coller dans une nouvelle query SQL Editor un simple `insert ... values (...) on conflict (simulation_id) do nothing;` (sans recréer toute la migration). Le `on conflict do nothing` ignorera proprement les sims déjà attribuées.
