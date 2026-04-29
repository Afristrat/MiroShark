# Plan d'exécution Ralph — MiroShark post-déploiement

> Stratégie de branche : **direct `main` avec commits atomiques par story** (choix utilisateur 4C).
> Stratégie de vérification : **build front + pytest + Playwright** (choix 2A + 3B).
> Périmètre : **7 chantiers, 35 stories** (choix 1A).
>
> **Total itérations Ralph : 35**
> **Signal de complétion : `<promise>COMPLETE</promise>`** (émis après la 35ᵉ story marquée `passes: true` ET après vérification finale des 4 quality gates : build front + pytest back + Playwright + healthcheck prod).
>
> **Exécution recommandée en 2 batches** (rappel CLAUDE.md global d'Amine : max 25 itérations sans intervention humaine) :
> - **Batch 1** : `US-000 → US-022` (23 itérations) — fondations + i18n + design + She Start + calibration
> - **Batch 2** : `US-023 → US-034` (12 itérations) — packaging + quick wins + hardening
>
> Commande ralph-loop pour chaque batch :
> ```bash
> ./ralph-loop.sh --target-branch main backlog.yaml          # tout en séquentiel
> # ou avec checkpoint manuel
> ./ralph-loop.sh --target-branch main --max-iterations 23 backlog.yaml
> ```

## Ordre d'exécution recommandé

### Sprint 1 — Fondations (≈ 2 jours)
1. `US-000` — Sécuriser pytest pour quality gates (bloquant tout le reste)
2. `US-031`, `US-032`, `US-033` — Hardening prod minimal (rapide, important pour la confiance des futures features)
3. `US-026` — Favicon HQ (quick win visible immédiatement)

### Sprint 2 — i18n FR/AR (≈ 5-6 jours)
1. `US-001` — Setup vue-i18n
2. `US-008` — LanguageSwitcher (en parallèle de 002+)
3. `US-002` → `US-006` — Externalisation textes par lots de vues (peuvent être parallélisés par chantier mais sur main donc séquentiel pour éviter conflits)
4. `US-007` — Backend error_codes
5. `US-009` — Support RTL complet (dépend de 002+003+008)
6. `US-010` — Tests Playwright multi-locale

### Sprint 3 — Finition design (≈ 2-3 jours)
1. `US-011` → `US-015` — Migration des 5 lots de composants/vues (parallélisables si l'agent travaille séquentiellement par fichier)
2. `US-016` — Audit final + cleanup CSS

### Sprint 4 — Templates She Start (≈ 2 jours)
1. `US-017` — Backend template
2. `US-018` — Seed document Markdown
3. `US-019` — Frontend Template Gallery card

### Sprint 5 — Calibration (≈ 2 jours)
1. `US-020` — Backend Brier score
2. `US-021` — Frontend page /calibration
3. `US-022` — 3 case studies retro (semi-manuel — Amine choisit les sujets)

### Sprint 6 — Packaging commercial (≈ 3 jours)
1. `US-023` — Page /offres
2. `US-024` — Génération PDF brandé (dépend du design finalisé)
3. `US-025` — Form devis + email

### Sprint 7 — Quick wins UI restants (≈ 2 jours)
1. `US-027` — Dark mode toggle (dépend du design finalisé)
2. `US-028` — Audit contraste WCAG AA
3. `US-029` — Animations scroll
4. `US-030` — Skeleton loaders

### Sprint 8 — Hardening avancé (≈ 1 jour)
1. `US-034` — Headers de sécurité

## Estimation totale
- **35 stories**
- **≈ 90 heures de travail** (estimations cumulées dans `prd.json`)
- **≈ 15-20 jours-Ralph** au rythme de 5-6 stories/jour si tout se passe bien

## Dépendances clés (graphe simplifié)

```
US-000 ─┬─ US-001 ─┬─ US-002 ─┬─ US-003
        │          │          ├─ US-004
        │          │          ├─ US-005
        │          │          └─ US-006
        │          ├─ US-008 ──┐
        │          └─ US-009 ◄─┘ (dépend aussi de 002+003)
        ├─ US-007 (dépend de 002)
        ├─ US-010 (dépend de 002+003+005+008+009)
        ├─ US-017 ─ US-018 ─ US-019 (dépend aussi de 002)
        ├─ US-020 ─ US-021 (dépend aussi de 002)
        │           └─ US-022
        ├─ US-031, US-032, US-033, US-034 (parallélisables)

(indépendants des autres) ─ US-011 → US-016
                          ─ US-023 → US-025 (dépend de 002 + 016)
                          ─ US-026 → US-030 (US-027 dépend de 016)
```

## Critères de "DONE" pour le projet entier

- [ ] 35/35 stories avec `passes: true` dans `.ralph/prd.json`
- [ ] `cd frontend && npm run build` retourne 0 sur `main`
- [ ] `cd backend && uv run pytest tests/ --tb=short -x` retourne 0
- [ ] `npx playwright test --reporter=list` passe vert
- [ ] `prospectives.ai-mpower.com` répond HTTP 200 sur `/`, `/verified`, `/offres`, `/calibration`
- [ ] Page `/offres` publique avec 3 packages
- [ ] Page `/calibration` publique avec Brier score réel ≥ 1 sim verified
- [ ] Template She Start utilisable par un client (interview Asma → seed doc → simulation)
- [ ] Aucun warning sécurité au pen test rapide (CORS, debug, secret key)

## Signal de fin

Une fois tous les critères ci-dessus satisfaits, l'agent Ralph émet **exactement** :

```
<promise>COMPLETE</promise>
```

Ce signal est :
- Émis **uniquement** après la 35ᵉ story `passes: true`
- Émis **uniquement** après revérification des 4 quality gates en condition réelle
- Émis **une seule fois** dans la dernière réponse de l'agent (pas dans un fichier)

Si l'un des critères est rouge → ne **pas** émettre le signal, documenter dans `progress.md` et alerter Amine.

## Politique de commit

Chaque story = **1 commit atomique sur `main`** au format :

```
[US-XXX] <titre court>

<description compacte>
- bullet 1 (acceptance criteria principal)
- bullet 2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Si une story nécessite plusieurs commits intermédiaires (rebase rare), squash avant push.

## Politique de quality gate

Avant de marquer `passes: true` sur une story :
1. `cd frontend && npm run build` → exit 0
2. `cd backend && uv run pytest tests/ --tb=short -x` → exit 0
3. Pour stories UI : `npx playwright test --reporter=list` → exit 0
4. Pas de console.error nouveau dans les pages touchées (vérification manuelle ou via Playwright)

Si l'un échoue → debug + relance, **ne pas marquer passes**.

## Circuit breaker

- Si une story échoue **3 fois** d'affilée avec la même erreur → stopper le loop, documenter dans `progress.md`, alerter Amine.
- Si le backend production est en restart loop pendant que Ralph tourne → stopper, ne jamais déployer une story qui aggrave la prod.
- Si les LLM credits Moonshot s'épuisent → stopper, demander à Amine.
