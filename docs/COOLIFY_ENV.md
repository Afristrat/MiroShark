# Variables d'environnement Coolify

Référence des variables d'env à configurer sur l'application Coolify
`miro-shark` (UUID `u6pn5mr2pgi88s13un55pkzb`) avant chaque démo prospect.

## SMTP — envoi des devis (US-025)

Sans ces variables, les demandes de devis postées via `/devis` sont
**enregistrées sur disque** dans `backend/uploads/quotes/quote_*.json`
mais **aucun email n'est envoyé**. Le formulaire répond quand même
`200 success` côté client (best-effort par design — on ne casse pas
l'UX si le SMTP est down).

### Variables obligatoires pour activer l'email

| Variable | Description | Exemple |
|---|---|---|
| `EMAIL_SMTP_HOST` | Hôte du serveur SMTP | `smtp.gmail.com` ou `smtp.sendgrid.net` |
| `EMAIL_SMTP_PORT` | Port SMTP (par défaut `587` STARTTLS) | `587` |
| `EMAIL_SMTP_USER` | Login SMTP | adresse email ou api-key |
| `EMAIL_SMTP_PASSWORD` | Mot de passe SMTP | **app password Gmail** ou clé API Sendgrid |

### Variables optionnelles (defaults raisonnables)

| Variable | Default | Description |
|---|---|---|
| `EMAIL_FROM` | `noreply@ai-mpower.com` | Adresse expéditeur |
| `EMAIL_TO` | `contact@ai-mpower.com` | Adresse destinataire (Amine) |

### Procédure Coolify

1. Coolify dashboard → application `miro-shark` → onglet **Environment Variables**
2. Cliquer **Add** pour chaque variable ci-dessus
3. Cocher **Build-time?** = NON (variables runtime uniquement)
4. Sauvegarder → Coolify déclenche un redeploy automatique
5. Vérifier en envoyant un devis test depuis `/devis` en prod
6. Confirmer la réception sur `EMAIL_TO`

### Procédure Gmail (recommandée pour démarrage rapide)

1. Compte Google AI MPOWER → **Security** → **2-step verification** (activer si pas déjà)
2. **App passwords** → générer un nouveau mot de passe pour « Bassira SMTP »
3. Copier le mot de passe 16 caractères
4. Sur Coolify :
   ```
   EMAIL_SMTP_HOST=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   EMAIL_SMTP_USER=fadilanassih@gmail.com
   EMAIL_SMTP_PASSWORD=<le mot de passe app de 16 caractères>
   EMAIL_FROM=fadilanassih@gmail.com
   EMAIL_TO=fadilanassih@gmail.com
   ```
5. Save + redeploy

### Récupération des devis stockés (si SMTP non actif)

```bash
# SSH sur le serveur Coolify ou via Coolify Terminal
docker exec -it <container_id_miroshark> ls /app/backend/uploads/quotes/
docker exec -it <container_id_miroshark> cat /app/backend/uploads/quotes/quote_<id>.json
```

Ou copie directe vers la machine locale via `docker cp`.

## LLM Moonshot (déjà configuré)

| Variable | Valeur prod actuelle |
|---|---|
| `LLM_BASE_URL` | `https://api.moonshot.ai/v1` |
| `LLM_MODEL_NAME` | `kimi-k2-turbo-preview` |
| `LLM_API_KEY` | (valeur sensible — rotée le 2026-04-29) |

## Neo4j (déjà configuré)

| Variable | Valeur prod actuelle |
|---|---|
| `NEO4J_URI` | (configuré sur Coolify) |
| `NEO4J_USER` | (configuré) |
| `NEO4J_PASSWORD` | (configuré, sensible) |

## Admin / divers

| Variable | Description |
|---|---|
| `BASSIRA_ADMIN_TOKEN` | Token Bearer pour les endpoints admin (resolve outcome, force delete, etc.). Vide en dev pour bypass auth. |
| `ORACLE_SEED_ENABLED` | `true`/`false` — active les oracle_tools dans les templates avec FeedOracle MCP. Default `false`. |

## Audit complet des env vars

```bash
# Sur Coolify dashboard, regarder l'onglet Environment Variables
# OU dans le container :
docker exec <container_id> printenv | grep -iE 'email|smtp|llm|neo4j|miroshark|oracle' | sort
```
