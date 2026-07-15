# Tests E2E Playwright — Bassira (US-010)

Suite de smoke tests **strictement read-only** ciblant la prod
`https://bassira.ma` ou un dev local via override.

## Périmètre

5 vues critiques × 3 langues (FR / AR / EN) :
- `/` (Home)
- `/calibration`
- `/offres`
- `/devis` (Step 1 affiché — **aucune soumission**)
- `/explore`

Plus deux suites transverses :
- `i18n-keys.spec.ts` — détection des clés i18n brutes ou placeholders non résolus
- `tunnel-commercial.spec.ts` — clic du CTA package → redirection /devis (stop avant submit)

## Installation locale

```bash
cd frontend
npm install
npm run test:e2e:install   # télécharge Chromium (~150 Mo, 1–2 min)
```

Le dernier script appelle `playwright install chromium --with-deps`.
Sur Windows, l'option `--with-deps` peut afficher un avertissement (les
packages système ne sont pas gérés sur Windows) ; ce n'est pas bloquant.

## Variables d'environnement

| Variable           | Default                                | Rôle                                       |
|--------------------|----------------------------------------|--------------------------------------------|
| `BASSIRA_E2E_URL`  | `https://bassira.ma`   | Base URL des tests (override pour le dev)  |
| `CI`               | unset                                  | Active retries=1 et workers=2              |

Exemples :

```bash
# Run sur la prod (par défaut)
npm run test:e2e

# Run en local (vite dev sur 5173)
BASSIRA_E2E_URL=http://localhost:5173 npm run test:e2e

# Mode UI Playwright pour debug
npm run test:e2e:ui

# Lister la collection sans exécuter (utile en CI offline)
npm run test:e2e:list
```

## Conventions Bassira (rappels)

- Locale via query param `?lang=fr|ar|en` (pris en charge par
  `frontend/src/i18n.js`, persiste en `localStorage.bassira_locale`).
- `<html dir="rtl">` automatiquement appliqué pour AR.
- `BASSIRA` est le nom de la marque (le backend reste `miroshark`).

## Read-only — règles strictes

- **Pas de création de simulation** sur `/` (la console n'est pas
  cliquée jusqu'au bout, on vérifie juste la présence du CTA).
- **Pas de soumission de formulaire devis** : les tests vérifient
  Step 1 et s'arrêtent. Aucun champ n'est rempli.
- **Pas de POST métier** : si un test casse cette règle, considérer
  qu'il pollue la prod avec un lead fantôme et le corriger immédiatement.

## Artefacts

- `frontend/test-results/` — traces, screenshots, vidéos en cas d'échec
- `frontend/playwright-report/` — HTML report (généré uniquement si on
  ajoute `reporter: ['list', 'html']` dans la config)

Ces deux dossiers sont gitignorés (voir `.gitignore` racine).

## Notes & limites connues

- **Régex i18n** (`i18n-keys.spec.ts`) : volontairement large pour
  attraper les clés brutes du type `home.hero.title`. Si un faux positif
  apparaît (ex: une URL légitime), ajouter le pattern à la `WHITELIST`
  dans `helpers.ts`.
- **RTL detection** : on vérifie `<html dir="rtl">`. Si un layout interne
  oublie de propager `dir`, le test ne le détectera pas — il faudrait
  une vérification plus poussée par composant.
- **Stabilité réseau** : `/calibration` fait un fetch backend, on alloue
  15 s pour la première stat card. Augmenter si le cold start Render
  est plus lent.
- **Browsers** : un seul project (`chromium`). Ajouter Webkit/Firefox
  uniquement si on a une régression cross-browser à investiguer.
