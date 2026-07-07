# App Spec — Bassira V2

> Source de vérité produit de la V2. Toute feature absente d'ici n'existe pas.
> Générée le 2026-07-07 depuis le cadrage `docs/np-cadrage.md` (verdict GO conditionnel).

## Problème et persona

**Persona** : dirigeant, directeur de la communication ou de la stratégie d'une entreprise
ou institution MENA (banque, énergie, secteur public, fonds, think tank) — cible confirmée
par le GTM existant (`bassira_brand_prompts.md:11-19`, matrice 3 tiers :
décideur économique / champion interne / sceptique technique).

**Le problème** : avant une décision exposée (lancement, communication de crise, politique
publique, restructuration), il n'a aucun moyen rapide de tester la réaction du public et
des parties prenantes. Aujourd'hui il contourne par : études de marché classiques
(semaines de délai, dizaines de milliers de MAD), conseil externe, ou instinct — et
découvre les objections APRÈS l'annonce.

## Solution en une phrase

**« Stress-testez votre décision avant de la prendre : des centaines de personas IA
débattent, tradent et changent d'avis pendant des heures simulées — vous recevez la
cartographie des réactions, des objections et des scénarios de dérapage, en 10 minutes. »**

⚠️ Positionnement V2 : **stress-test de décision**, PAS « prédiction du réel ». Le claim
prédictif (« Brier vérifié », « called it ») est abandonné tant qu'aucun outcome public
réel ne l'étaye (ADR-002 — fondement : Bisbee 2024, thèse inverse de Simile).

## Parcours critique (V2 — écran par écran)

| # | Écran | Qui | LA chose qu'on y fait |
|---|---|---|---|
| 1 | `/login` → `/console` | Client org | S'authentifier, choisir son organisation (sélecteur global persistant) |
| 2 | `/` (console) — nouvelle simulation | Client | Déposer un document/scénario OU poser une question (Smart Setup) |
| 3 | `/process/:id` → `/review-entities/:id` | Client | Valider les entités extraites (pre-check bloquant si graphe vide) |
| 3bis | Config simulation | Client | Choisir ses ARÈNES (réseaux simulés, marché de prédiction, arènes MENA — US-216) et la langue du livrable |
| 4 | `/simulation/:id` | Client | Lancer et suivre le run (timeline heure par heure, Director Mode) |
| 5 | `/report/:id` | Client | Lire le rapport, ouvrir l'encart « limites et méthode » (obligatoire) |
| 6 | Livraison PDF | Client/Admin | Recevoir le PDF brandé par URL signée + email (SMTP opérationnel) |
| 7 | `/offres` → Stripe Checkout | Prospect | Payer un package en self-service (US-113 terminée) |

Sans les écrans 2→6, l'app n'a aucune valeur. L'écran 7 est la condition de revenu self-serve.

## Modèle de revenu

- **Devis B2B** (existant, canal principal) : packages 12 000 / 35 000 / 20 000 MAD —
  $1.2k / $3.5k / $2k USD — **jamais EUR** (règle durable, PASSATION.md:1386).
- **Self-service Stripe** (V2, US-113) : achat de packages en ligne pour le tier bas.
- Coût variable par run : ~1-3,50 $ de LLM (BYOK : le client peut apporter sa clé —
  argument souveraineté).

## Écosystème (directives Amine 2026-07-07)

- **Saqr** (ex-Kairos) et **Nahda** CONSOMMENT les sorties de Bassira (contrat API
  sortant : US-218) — en plus du flux entrant existant Bassira→Saqr (recherche from-seed).
- **Deux canaux de prospective** cohabiteront : **Bassira = B2B** ; un canal basé
  **MiroFish** (jugé plus adéquat par Amine) pour les **grandes missions et le B2G**, au
  service de Nahda. Cadrage MiroFish : faits en cours de collecte (agent upstream-mirofish).
- **Arènes de simulation configurables** : le marché de prédiction (mécanisme occidental)
  n'est plus la seule arène — l'utilisateur choisit par simulation ses arènes, dont des
  arènes adaptées Africa/Middle East (US-216).
- Domaine public : **bassira.ma toujours**.

## Ce que la V2 EXCLUT (les refus explicites)

1. **Réécriture big-bang non décidée** — la réécriture mono-stack est une option OUVERTE
   qu'Amine accepte (ADR-010) ; ce qui est exclu, c'est de l'engager sans décision ADR
   explicite et sans le retour des faits MiroFish/upstream.
2. **Claim prédictif et « calibration vérifiée »** tant que < 20 outcomes réels marqués
   publiquement — le mot « prédiction » disparaît du copy commercial. (ADR-002)
3. **Scaling multi-nœud** (queue distribuée, workers multiples pour le moteur) — hors
   périmètre tant que < 10 orgs actives simultanées ; l'architecture mono-nœud durcie
   (WSGI + Redis PDF) suffit. (parking lot)
4. **Nouveau canal PLG grand public** (freemium à la Artificial Societies, 40 $/mois) —
   le positionnement institutionnel sur devis est un choix assumé. (parking lot,
   condition de sortie : 3 refus prospects pour cause de prix d'entrée)
5. **Mobile / app native** — usage desktop C-Level confirmé, rien ne justifie l'effort.

## Hypothèses restantes

| Hypothèse | Test | Critère de réfutation | Échéance |
|---|---|---|---|
| Le framing « stress-test » lève l'objection de crédibilité | 3 démos prospects pipeline Apollo, framing A/B | 3/3 jugent « gadget » même reframé | 2026-07-21 |
| Une licence commerciale MiroShark est négociable | Contact aaronjmars | Refus ou silence > 30 j → arbitrer publier vs réécrire | 2026-08-07 |
| Il existe ≥ 1 client prêt à payer 12k MAD | Pipeline Apollo → 1 devis signé | 0 signature après 20 séquences complètes | 2026-09-30 |
| L'ancrage Saqr (signaux réels) augmente la crédibilité perçue | Démo avec/sans calibration signaux | Aucun prospect ne relève la différence | 2026-09-30 |
| Une arène MENA (hors marché de prédiction) produit un signal exploitable | Prototype d'arène + comparaison avec l'arène marché sur un même scénario | Indicateur agrégé illisible ou non discriminant | 2026-09-30 |

## Traçabilité

Verdict : **GO conditionnel** (3 conditions bloquantes — voir `docs/np-cadrage.md` § Verdict)
· Niveau : **L6** · Cadrage : `docs/np-cadrage.md` · Base : MiroShark upstream
(`aaronjmars/miroshark`, AGPL-3.0) + couche Bassira (134 US, `.ralph/prd.json`).
