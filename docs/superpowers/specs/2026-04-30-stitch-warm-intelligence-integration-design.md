# Spec — Intégration Warm Intelligence dans les vues Vue.js Bassira

**Date :** 2026-04-30  
**Scope :** 5 vues Vue.js — Home, Offres, Calibration, Devis, Insights  
**Maquettes approuvées :** `.superpowers/brainstorm/1517-1777558181/content/*-v3.html`  
**Cible :** C-Levels, ministres, directeurs de think-tank, entrepreneurs MENA

---

## 1. Contexte et objectif

Le design system Stitch "Warm Intelligence" a été livré après que les stories US-021/023/025 aient été marquées `passes:true`. Aucune story Ralph ne couvre encore l'intégration. Ce document spécifie la refonte pixel-perfect des 5 vues frontales de Bassira.

**Contraintes dures :**
- Conserver le carousel avec les 10 packages dans `OffersView.vue` (pas de grille statique)
- Conserver le D3 SVG scatter plot dans `CalibrationView.vue` — re-skinning couleurs uniquement
- Préserver tous les bindings Vue : `v-if`, `v-for`, `v-model`, `$t()`, `router-link`, `@click`
- Devises : MAD / USD uniquement — jamais EUR
- i18n : clés `$t()` conservées, copywriting C-Level injecté dans `fr.json` / `en.json` / `ar.json`

---

## 2. Design system — tokens Warm Intelligence

Les tokens sont déjà dans `frontend/src/design-tokens.css`. La refonte utilise ces valeurs existantes sans en ajouter de nouvelles.

| Token | Valeur | Usage |
|---|---|---|
| `--ms-orange` | `#FF8551` | Primary, CTA, accent |
| `--ms-orange-light` | `#ffdbce` | Primary-container, badges |
| `--ms-bg` | `#FAF7F2` | Surface (fond page) |
| `--ms-surface` | `#fff8f6` | Cards, nav |
| `--ms-on-surface` | `#241915` | Texte principal |
| `--ms-on-surface-variant` | `#57423a` | Texte secondaire |
| `--ms-outline-variant` | `#dec0b6` | Bordures, séparateurs |
| `--ms-surface-container` | `#f5ede9` | Sections alternées |
| `--ms-radius-lg` | `24px` | Cards principales |
| `--ms-radius-md` | `16px` | Sous-éléments |
| `--ms-shadow-lg` | `0px 12px 32px rgba(74,69,64,0.08)` | Cards |
| Font heading | Outfit (300–900) | Titres, labels, CTA |
| Font body | Manrope (300–700) | Corps de texte |

---

## 3. Architecture — vues à créer ou modifier

### 3.1 Vues existantes modifiées (template + CSS scoped)

| Vue | Fichier | Nature de la modification |
|---|---|---|
| Home | `frontend/src/views/Home.vue` | Refonte complète du template (landing marketing) |
| Offres | `frontend/src/views/OffersView.vue` | Re-skin template, carousel conservé |
| Calibration | `frontend/src/views/CalibrationView.vue` | Re-skin template, D3 chart conservé |
| Devis | `frontend/src/views/QuoteView.vue` | Re-skin template, stepper conservé |

### 3.2 Vue nouvelle à créer

| Vue | Fichier | Nature |
|---|---|---|
| Insights | `frontend/src/views/InsightsView.vue` | Nouvelle vue — liste de briefs paginée |

### 3.3 Composants nouveaux à créer

| Composant | Fichier | Usage |
|---|---|---|
| AppNav | `frontend/src/components/AppNav.vue` | Nav sticky partagée entre toutes les vues |
| AppFooter | `frontend/src/components/AppFooter.vue` | Footer partagé |
| TagBadge | `frontend/src/components/TagBadge.vue` | Badge pill réutilisable (couleur + texte) |
| BriefCard | `frontend/src/components/BriefCard.vue` | Card d'un brief Insights |

### 3.4 Router

Ajouter la route `/insights` dans le fichier router existant.

---

## 4. Détail par vue

### 4.1 Home (`Home.vue`)

**Sections (ordre vertical) :**
1. `AppNav` sticky
2. Hero full-height : headline "Décidez mieux. Prouvé.", badge trust Brier, 2 CTA (Voir les protocoles / Score Brier public), trust strip clients en bas
3. Bande stats sombre `#241915` : 0.18 / 47 / 66% / 48h
4. Section 3 protocoles : grille 3 colonnes statique (Home uniquement — le carousel est réservé à /offres)
5. Section processus 3 étapes + 3 guarantee cards
6. Section derniers briefs (3 BriefCard statiques, lien vers /insights)
7. CTA final fond sombre
8. `AppFooter`

**Bindings conservés :** `$t()` sur tous les textes, `router-link` sur les CTA, `@click="scrollToTemplates"` si existant.

---

### 4.2 Offres (`OffersView.vue`)

**Sections :**
1. `AppNav`
2. Hero : headline `$t('offers.hero.title')`, badge Brier, sous-titre
3. Filter chips (existants, re-skinnés) — `v-for` sur categories
4. Carousel (existant, re-skinné) — cards avec `v-for` sur packages, `v-if` pour badge featured
5. FAQ `details/summary` — `v-for` sur faq items
6. Pre-footer CTA "Soumettre votre cas"
7. `AppFooter`

**Carousel :** conserver la logique JS existante (prev/next, dots, auto-scroll). Re-skinner uniquement : card background blanc, radius 24px, shadow `--ms-shadow-lg`, couleurs tokens.

---

### 4.3 Calibration (`CalibrationView.vue`)

**Sections :**
1. `AppNav`
2. Hero Brier : chiffre 120px Outfit Black, delta badge vert, headline, sous-titre méthodologie
3. 4 stat cards : 47 / 31 / 11 / 5 — `v-for` existant re-skinné
4. Zone chart D3 : wrapper re-skinné, nodes colorés `--ms-orange`, sidebar avec selects (existants)
5. Section méthodologie : 3 engagements (horodatage public / jamais supprimé / scoring indépendant)
6. CTA test prévision
7. `AppFooter`

**D3 chart :** modifier uniquement les couleurs des nodes SVG — remplacer la couleur hardcodée par `var(--ms-orange)` via `getComputedStyle`. Ne pas toucher à la logique de calcul ni au layout SVG.

---

### 4.4 Devis (`QuoteView.vue`)

**Sections :**
1. `AppNav` + trust bar "Traité directement par les fondateurs"
2. Header : headline, tag badge, sous-titre
3. Stepper 3 étapes (existant, re-skinné) — dots orange/gris, labels
4. Card formulaire 640px centrée :
   - Step 1 : 4 radio cards avec persona-targeting (Crise / Politique / Lancement / Autre)
   - Step 2 : floating-label inputs + audience chips
   - Step 3 : package match card `#ffdbce` + textarea contexte + checkbox RGPD
   - Step 4 (success) : état succès avec référence #BSR-XXXX
5. 3 guarantee stats (5 000+ / Air-gap / 48h)
6. `AppFooter`

**Bindings conservés :** `v-model` sur inputs, `@submit` existant, `$t()` sur labels.

---

### 4.5 Insights (`InsightsView.vue`) — nouvelle vue

**Sections :**
1. `AppNav` (lien "Insights" actif)
2. Hero : "Ce que nous avons prévu. Ce qui s'est passé.", sous-titre transparence
3. Stats strip : 47 / 0.18 / 66% / 3 domaines
4. Filter chips : Tous / Politique publique / Crise / Marketing / Prévisions ouvertes / Vérifiées
5. Brief à la une : card sombre `#241915`, featured
6. Grille 3 colonnes de `BriefCard` — données mockées en attendant API
7. Bouton "Charger plus" (pagination future)
8. Section newsletter : input email + bouton S'inscrire
9. `AppFooter`

**Données :** tableau statique de briefs mockés dans le composant (`data()` ou `ref()`). Structure :
```ts
interface Brief {
  id: string
  title: string
  category: 'politique' | 'crise' | 'marketing'
  date: string
  brierScore: number | null
  status: 'verified' | 'open'
  readingMinutes: number
  excerpt: string
  accuracy?: number
}
```

---

## 5. i18n — clés à ajouter

Les clés suivantes sont à ajouter dans `fr.json`, `en.json`, `ar.json` :

```
home.hero.title, home.hero.subtitle, home.hero.ctaProtocols, home.hero.ctaBrier
home.stats.brier, home.stats.predictions, home.stats.accuracy, home.stats.setup
home.protocols.title, home.process.title, home.cta.title
insights.hero.title, insights.hero.subtitle
insights.filter.all, insights.filter.politique, insights.filter.crise, insights.filter.marketing
insights.filter.open, insights.filter.verified
insights.newsletter.title, insights.newsletter.cta
nav.insights
```

---

## 6. Ordre de livraison

1. `AppNav.vue` + `AppFooter.vue` + `TagBadge.vue` — composants partagés
2. `Home.vue` — landing page
3. `OffersView.vue` — carousel re-skinné
4. `CalibrationView.vue` — D3 re-coloré
5. `QuoteView.vue` — stepper re-skinné
6. `InsightsView.vue` + `BriefCard.vue` — nouvelle vue
7. Router : ajout route `/insights`
8. i18n : toutes les clés nouvelles dans fr/en/ar

**Validation après chaque vue :** `npm run typecheck && npm run lint`. Zéro erreur avant de passer à la suivante.

---

## 7. Ce qui ne change PAS

- La logique métier (API calls, simulation engine, Supabase)
- Les routes existantes (sauf ajout `/insights`)
- Les composants internes (SettingsPanel, TemplateGallery, etc.)
- Le fichier `design-tokens.css` (déjà correct)
- Les tests Playwright existants
